import os
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, NetworkError, TelegramError, TimedOut, Unauthorized

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel
from src.models.ticket import Ticket
from src.models.video import Video
from src.services.messenger_service import (
    MessengerError,
    MessengerService,
    RateLimitExceededError,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl_store: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def incr(self, key: str) -> int:
        current = int(self.store.get(key, "0"))
        new_value = current + 1
        self.store[key] = str(new_value)
        return new_value

    def expire(self, key: str, seconds: int) -> bool:
        self.ttl_store[key] = seconds
        return True

    def ttl(self, key: str) -> int:
        return self.ttl_store.get(key, -1)


@pytest.fixture(scope="module")
def app():
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    test_app = create_app("development")
    test_app.config["TESTING"] = True
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def cleanup_db(app):
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def fake_redis(monkeypatch):
    store = FakeRedis()
    monkeypatch.setattr("src.services.messenger_service.redis.from_url", lambda *_, **__: store)
    return store


@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.get_me.return_value = MagicMock(username="test_bot", id=123456)
    return bot


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.TELEGRAM_BOT_TOKEN = "test_token"
    config.TELEGRAM_WEBHOOK_SECRET = "test_secret"
    config.TELEGRAM_ESCALATION_CHANNEL = "-4672336726"
    config.TELEGRAM_PRIMARY_CHANNEL = "-4672336726"
    config.TELEGRAM_RETRY_ATTEMPTS = 3
    config.TELEGRAM_RETRY_DELAY = 2
    config.TELEGRAM_RATE_LIMIT_MAX = 10
    config.REDIS_URL = "redis://localhost:6379/0"
    return config


@pytest.fixture
def messenger_service(mock_config, fake_redis, mock_bot):
    with patch("src.services.messenger_service.Bot", return_value=mock_bot):
        with patch("src.services.messenger_service.get_config", return_value=mock_config):
            service = MessengerService(config=mock_config)
            service.redis_client = fake_redis
            service.bot = mock_bot
            return service


@pytest.fixture
def test_video(app):
    with app.app_context():
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
def test_ticket(app, test_video):
    with app.app_context():
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
        # Refresh to load relationships
        db.session.refresh(ticket)
        return ticket


class TestMessengerService:
    def test_initialization_success(self, mock_config, fake_redis, mock_bot):
        with patch("src.services.messenger_service.Bot", return_value=mock_bot):
            with patch("src.services.messenger_service.get_config", return_value=mock_config):
                service = MessengerService(config=mock_config)
                service.redis_client = fake_redis
                service.bot = mock_bot

                assert service.bot is not None
                assert service.redis_client is not None
                assert service.jinja_env is not None
                assert service.primary_channel == "-4672336726"
                assert service.escalation_channel == "-4672336726"

    def test_initialization_invalid_token(self, mock_config, fake_redis):
        mock_bot = MagicMock(spec=Bot)
        mock_bot.get_me.side_effect = Unauthorized("Invalid token")

        with patch("src.services.messenger_service.Bot", return_value=mock_bot):
            with patch("src.services.messenger_service.get_config", return_value=mock_config):
                service = MessengerService(config=mock_config)
                service.redis_client = fake_redis

                # Bot should be None on initialization failure
                assert service.bot is None

    def test_send_alert_success(self, messenger_service, test_ticket):
        messenger_service.bot.send_message.return_value = MagicMock()

        success, error = messenger_service.send_alert(test_ticket)

        assert success is True
        assert error is None
        messenger_service.bot.send_message.assert_called_once()
        assert messenger_service.bot.send_message.call_args[1]["chat_id"] == "-4672336726"

    def test_send_alert_with_image(self, messenger_service, test_ticket, tmp_path):
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"fake image data")
        messenger_service.bot.send_photo.return_value = MagicMock()

        success, error = messenger_service.send_alert(test_ticket, image_path=str(image_path))

        assert success is True
        assert error is None
        messenger_service.bot.send_photo.assert_called_once()
        assert messenger_service.bot.send_message.call_count == 0

    def test_send_alert_with_audio(self, messenger_service, test_ticket, tmp_path):
        audio_path = tmp_path / "test.wav"
        audio_path.write_bytes(b"fake audio data")
        messenger_service.bot.send_audio.return_value = MagicMock()

        success, error = messenger_service.send_alert(test_ticket, audio_path=str(audio_path))

        assert success is True
        assert error is None
        messenger_service.bot.send_audio.assert_called_once()
        assert messenger_service.bot.send_message.call_count == 0

    def test_send_alert_rate_limit_exceeded(self, messenger_service, test_ticket, fake_redis):
        # Set rate limit to max
        fake_redis.store["telegram:rate_limit:-4672336726"] = "10"

        success, error = messenger_service.send_alert(test_ticket)

        assert success is False
        assert isinstance(error, RateLimitExceededError)
        messenger_service.bot.send_message.assert_not_called()

    def test_send_alert_retry_success_on_second_attempt(self, messenger_service, test_ticket):
        # First call fails, second succeeds
        messenger_service.bot.send_message.side_effect = [
            NetworkError("Network error"),
            MagicMock(),
        ]

        with patch("time.sleep"):  # Don't actually sleep in tests
            success, error = messenger_service.send_alert(test_ticket)

        assert success is True
        assert error is None
        assert messenger_service.bot.send_message.call_count == 2

    def test_send_alert_all_retries_fail(self, messenger_service, test_ticket):
        messenger_service.bot.send_message.side_effect = NetworkError("Network error")

        with patch("time.sleep"):  # Don't actually sleep in tests
            success, error = messenger_service.send_alert(test_ticket)

        assert success is False
        assert error is not None
        assert messenger_service.bot.send_message.call_count == 4  # 1 initial + 3 retries

    def test_send_escalation_alert_success(self, messenger_service, test_ticket):
        messenger_service.bot.send_message.return_value = MagicMock()

        success, error = messenger_service.send_escalation_alert(test_ticket)

        assert success is True
        assert error is None
        messenger_service.bot.send_message.assert_called_once()
        assert messenger_service.bot.send_message.call_args[1]["chat_id"] == "-4672336726"

    def test_check_rate_limit_within_limit(self, messenger_service, fake_redis):
        fake_redis.store["telegram:rate_limit:-4672336726"] = "5"

        result = messenger_service._check_rate_limit("-4672336726")

        assert result is True

    def test_check_rate_limit_exceeded(self, messenger_service, fake_redis):
        fake_redis.store["telegram:rate_limit:-4672336726"] = "10"

        result = messenger_service._check_rate_limit("-4672336726")

        assert result is False

    def test_increment_rate_limit(self, messenger_service, fake_redis):
        messenger_service._increment_rate_limit("-4672336726")

        count = fake_redis.get("telegram:rate_limit:-4672336726")
        assert count == "1"

        # Increment again
        messenger_service._increment_rate_limit("-4672336726")
        count = fake_redis.get("telegram:rate_limit:-4672336726")
        assert count == "2"

    def test_render_alert_template_critical(self, messenger_service, test_ticket):
        test_ticket.threat_level = ThreatLevel.CRITICAL

        message = messenger_service._render_alert_template(test_ticket, "alert")

        assert message is not None
        assert "🚨" in message
        assert "CRITICAL" in message
        assert test_ticket.title in message

    def test_render_alert_template_low(self, messenger_service, test_ticket):
        test_ticket.threat_level = ThreatLevel.LOW

        message = messenger_service._render_alert_template(test_ticket, "alert")

        assert message is not None
        assert "ℹ️" in message
        assert "LOW" in message

    def test_create_inline_keyboard(self, messenger_service):
        from src.config.constants import TelegramCallbackAction
        
        ticket_id = "test-ticket-id"
        keyboard = messenger_service._create_inline_keyboard(ticket_id)

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        button = keyboard.inline_keyboard[0][0]
        assert isinstance(button, InlineKeyboardButton)
        assert button.text == "✅ Acknowledge"
        assert button.callback_data == f"{TelegramCallbackAction.ACKNOWLEDGE}:{ticket_id}"

    def test_handle_callback_acknowledge_success(self, messenger_service, test_ticket):
        from src.config.constants import TelegramCallbackAction
        
        with patch("src.services.messenger_service.TicketService") as mock_ticket_service:
            mock_service_instance = MagicMock()
            mock_service_instance.acknowledge_ticket.return_value = (test_ticket, None)
            mock_ticket_service.return_value = mock_service_instance

            success, error = messenger_service.handle_callback(
                f"{TelegramCallbackAction.ACKNOWLEDGE}:{test_ticket.id}", {"id": 12345, "username": "testuser"}
            )

            assert success is True
            assert error is None
            mock_service_instance.acknowledge_ticket.assert_called_once_with(
                test_ticket.id, user_id=None
            )

    def test_handle_callback_acknowledge_error(self, messenger_service, test_ticket):
        with patch("src.services.messenger_service.TicketService") as mock_ticket_service:
            mock_service_instance = MagicMock()
            mock_service_instance.acknowledge_ticket.return_value = (
                None,
                MessengerError("Ticket not found"),
            )
            mock_ticket_service.return_value = mock_service_instance

            success, error = messenger_service.handle_callback(
                f"acknowledge:{test_ticket.id}", {"id": 12345, "username": "testuser"}
            )

            assert success is False
            assert error is not None

    def test_handle_callback_invalid_action(self, messenger_service):
        success, error = messenger_service.handle_callback(
            "invalid_action:ticket-id", {"id": 12345}
        )

        assert success is False
        assert isinstance(error, MessengerError)

    def test_exponential_backoff_delays(self, messenger_service, test_ticket):
        messenger_service.bot.send_message.side_effect = NetworkError("Network error")
        sleep_calls = []

        def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("time.sleep", side_effect=mock_sleep):
            messenger_service._send_message_with_retry(
                channel_id="-4672336726", text="Test message"
            )

        # Should have 3 sleep calls (before 2nd, 3rd, and 4th attempts)
        # Delays: 2s, 4s, 8s for attempts 1, 2, 3
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 2  # First retry delay (attempt 1)
        assert sleep_calls[1] == 4  # Second retry delay (attempt 2: 2 * 2)
        assert sleep_calls[2] == 8  # Third retry delay (attempt 3: 2 * 4)

    def test_send_alert_bot_not_initialized(self, mock_config, fake_redis):
        with patch("src.services.messenger_service.Bot", return_value=None):
            with patch("src.services.messenger_service.get_config", return_value=mock_config):
                service = MessengerService(config=mock_config)
                service.redis_client = fake_redis
                service.bot = None

                ticket = MagicMock(spec=Ticket)
                ticket.id = "test-id"
                ticket.title = "Test"
                ticket.description = "Test"
                ticket.priority = TicketPriority.MEDIUM
                ticket.status = TicketStatus.OPEN
                ticket.threat_level = ThreatLevel.MEDIUM
                ticket.created_at = datetime.utcnow()

                success, error = service.send_alert(ticket)

                assert success is False
                assert isinstance(error, MessengerError)

    def test_check_rate_limit_redis_unavailable(self, messenger_service):
        messenger_service.redis_client = None

        # Should return True (graceful degradation)
        result = messenger_service._check_rate_limit("-4672336726")
        assert result is True

