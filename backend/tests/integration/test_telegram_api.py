import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from telegram import Bot
from telegram.error import TelegramError

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel
from src.config.settings import get_config
from src.models.ticket import Ticket
from src.models.user import User
from src.models.video import Video
from src.services.auth_service import AuthService


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def incr(self, key: str) -> int:
        current = int(self.store.get(key, "0"))
        new_value = current + 1
        self.store[key] = str(new_value)
        return new_value

    def expire(self, key: str, seconds: int) -> bool:
        return True

    def ttl(self, key: str) -> int:
        return 60


@pytest.fixture(scope="session")
def app_fixture(monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    fake_redis = FakeRedis()
    counters = {"access": 0, "refresh": 0}

    def fake_create_access_token(identity):
        counters["access"] += 1
        user_id = getattr(identity, "id", identity)
        return f"access-token-{user_id}-{counters['access']}"

    def fake_create_refresh_token(identity):
        counters["refresh"] += 1
        user_id = getattr(identity, "id", identity)
        return f"refresh-token-{user_id}-{counters['refresh']}"

    monkeypatch.setattr("src.services.auth_service.create_access_token", fake_create_access_token)
    monkeypatch.setattr("src.services.auth_service.create_refresh_token", fake_create_refresh_token)
    monkeypatch.setattr("src.services.messenger_service.redis.from_url", lambda *_, **__: fake_redis)

    test_app = create_app("development")
    test_app.config["TESTING"] = True
    test_app.config["JWT_SECRET_KEY"] = "test-secret-key"

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def cleanup_db(app_fixture):
    with app_fixture.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def client(app_fixture):
    return app_fixture.test_client()


@pytest.fixture
def admin_user(app_fixture):
    with app_fixture.app_context():
        user = User(
            username="admin",
            email="admin@test.com",
            role="admin",
            is_active=True,
        )
        user.set_password("admin123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def staff_user(app_fixture):
    with app_fixture.app_context():
        user = User(
            username="staff",
            email="staff@test.com",
            role="staff",
            is_active=True,
        )
        user.set_password("staff123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_token(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    data = response.get_json()
    return data["access_token"]


@pytest.fixture
def staff_token(client, staff_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "staff", "password": "staff123"},
    )
    data = response.get_json()
    return data["access_token"]


@pytest.fixture
def test_video(app_fixture):
    with app_fixture.app_context():
        video = Video(
            filename="test_video.mp4",
            filepath="/test/path/test_video.mp4",
            duration=100.0,
            status="ready",
            upload_type="upload",
        )
        db.session.add(video)
        db.session.commit()
        return video


@pytest.fixture
def test_ticket(app_fixture, test_video):
    with app_fixture.app_context():
        ticket = Ticket(
            video_id=test_video.id,
            title="Suspicious Activity Detected",
            description="Test description",
            priority=TicketPriority.HIGH,
            status=TicketStatus.OPEN,
            threat_level=ThreatLevel.HIGH,
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket


@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.get_me.return_value = MagicMock(username="test_bot", id=123456)
    bot.answer_callback_query.return_value = MagicMock()
    bot.edit_message_reply_markup.return_value = MagicMock()
    bot.send_message.return_value = MagicMock()
    bot.set_webhook.return_value = True
    bot.delete_webhook.return_value = True
    bot.get_webhook_info.return_value = MagicMock(
        url="https://example.com/webhook",
        has_custom_certificate=False,
        pending_update_count=0,
        last_error_date=None,
        last_error_message=None,
    )
    return bot


def create_webhook_payload(callback_data: str, user_id: int = 12345):
    return {
        "update_id": 123456789,
        "callback_query": {
            "id": "callback-123",
            "from": {
                "id": user_id,
                "username": "testuser",
                "first_name": "Test",
            },
            "message": {
                "chat": {"id": -4672336726},
                "message_id": 456,
            },
            "data": callback_data,
        },
    }


class TestTelegramAPI:
    def test_webhook_callback_acknowledge_success(
        self, client, test_ticket, mock_bot
    ):
        config = get_config()
        webhook_secret = config.TELEGRAM_WEBHOOK_SECRET

        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            with patch(
                "src.services.messenger_service.MessengerService.handle_callback"
            ) as mock_handle:
                mock_handle.return_value = (True, None)

                from src.config.constants import TelegramCallbackAction
                payload = create_webhook_payload(f"{TelegramCallbackAction.ACKNOWLEDGE}:{test_ticket.id}")

                response = client.post(
                    "/api/telegram/webhook",
                    json=payload,
                    headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data["status"] == "ok"

                # Verify ticket was acknowledged
                with client.application.app_context():
                    db.session.refresh(test_ticket)
                    # Note: The actual acknowledgment happens in handle_callback
                    # which is mocked, so we verify the mock was called
                    mock_handle.assert_called_once()

    def test_webhook_callback_invalid_secret(self, client, test_ticket):
        payload = create_webhook_payload(f"acknowledge:{test_ticket.id}")

        response = client.post(
            "/api/telegram/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data

    def test_webhook_callback_missing_secret(self, client, test_ticket):
        payload = create_webhook_payload(f"acknowledge:{test_ticket.id}")

        response = client.post("/api/telegram/webhook", json=payload)

        assert response.status_code == 403

    def test_webhook_callback_ticket_not_found(self, client, mock_bot):
        config = get_config()
        webhook_secret = config.TELEGRAM_WEBHOOK_SECRET

        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            with patch(
                "src.services.messenger_service.MessengerService.handle_callback"
            ) as mock_handle:
                from src.services.messenger_service import MessengerError

                mock_handle.return_value = (False, MessengerError("Ticket not found"))

                payload = create_webhook_payload("acknowledge:nonexistent-ticket-id")

                response = client.post(
                    "/api/telegram/webhook",
                    json=payload,
                    headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
                )

                # Always return 200 to Telegram
                assert response.status_code == 200

    def test_webhook_callback_already_acknowledged(
        self, client, test_ticket, mock_bot
    ):
        config = get_config()
        webhook_secret = config.TELEGRAM_WEBHOOK_SECRET

        # Set ticket to acknowledged
        with client.application.app_context():
            test_ticket.status = TicketStatus.ACKNOWLEDGED
            db.session.commit()

        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            with patch(
                "src.services.messenger_service.MessengerService.handle_callback"
            ) as mock_handle:
                from src.services.messenger_service import MessengerError

                mock_handle.return_value = (
                    False,
                    MessengerError("Ticket already acknowledged"),
                )

                from src.config.constants import TelegramCallbackAction
                payload = create_webhook_payload(f"{TelegramCallbackAction.ACKNOWLEDGE}:{test_ticket.id}")

                response = client.post(
                    "/api/telegram/webhook",
                    json=payload,
                    headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
                )

                assert response.status_code == 200

    def test_set_webhook_as_admin(self, client, admin_token, mock_bot):
        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            response = client.post(
                "/api/telegram/set-webhook",
                json={"webhook_url": "https://example.com/api/telegram/webhook"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert "url" in data
            mock_bot.set_webhook.assert_called_once()

    def test_set_webhook_as_staff(self, client, staff_token):
        response = client.post(
            "/api/telegram/set-webhook",
            json={"webhook_url": "https://example.com/api/telegram/webhook"},
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 403

    def test_set_webhook_invalid_url(self, client, admin_token):
        response = client.post(
            "/api/telegram/set-webhook",
            json={"webhook_url": "http://example.com/webhook"},  # HTTP not HTTPS
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "HTTPS" in data["error"]

    def test_delete_webhook_as_admin(self, client, admin_token, mock_bot):
        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            response = client.post(
                "/api/telegram/delete-webhook",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            mock_bot.delete_webhook.assert_called_once()

    def test_get_webhook_info_as_admin(self, client, admin_token, mock_bot):
        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            response = client.get(
                "/api/telegram/webhook-info",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "url" in data
            assert "pending_update_count" in data
            mock_bot.get_webhook_info.assert_called_once()

    def test_webhook_callback_malformed_payload(self, client, mock_bot):
        config = get_config()
        webhook_secret = config.TELEGRAM_WEBHOOK_SECRET

        with patch("src.api.telegram.messenger_service.bot", mock_bot):
            # Send malformed JSON
            response = client.post(
                "/api/telegram/webhook",
                data="not json",
                headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
            )

            # Should still return 200 (graceful handling)
            assert response.status_code == 200

    def test_cors_headers(self, client, admin_token):
        response = client.options(
            "/api/telegram/set-webhook",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # CORS should be configured for /api/* routes
        assert response.status_code in [200, 204]

