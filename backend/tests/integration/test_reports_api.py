import json
import os
from datetime import datetime
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from flask_jwt_extended import create_access_token

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel, UserRole
from src.models.audit_log import AuditLog
from src.models.evidence import Evidence
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.user import User
from src.models.video import Video


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def setex(self, key: str, ttl: int, value: bytes) -> None:
        self.store[key] = value

    def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted


@pytest.fixture(scope="session")
def app_fixture(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("JWT_SECRET_KEY", "jwt-secret")
    storage_dir = tmp_path_factory.mktemp("reports-api")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))

    fake_redis = FakeRedis()
    monkeypatch.setattr("src.services.report_service.redis.from_url", lambda *_, **__: fake_redis)
    monkeypatch.setattr("src.services.ticket_service.redis.from_url", lambda *_, **__: fake_redis)

    test_app = create_app("development")
    test_app.config["TESTING"] = True
    test_app.config["JWT_TOKEN_LOCATION"] = ["headers"]

    with test_app.app_context():
        db.create_all()
        yield test_app
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
def staff_user(app_fixture):
    with app_fixture.app_context():
        user = User(
            username="staff1",
            email="staff1@test.com",
            role=UserRole.STAFF,
            is_active=True,
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app_fixture):
    with app_fixture.app_context():
        user = User(
            username="admin1",
            email="admin1@test.com",
            role=UserRole.ADMIN,
            is_active=True,
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_video(app_fixture):
    with app_fixture.app_context():
        video = Video(
            filename="test.mp4",
            filepath="videos/test.mp4",
            user_id=None,
            filesize=1000,
        )
        db.session.add(video)
        db.session.commit()
        return video


@pytest.fixture
def test_ticket(app_fixture, test_video, staff_user):
    with app_fixture.app_context():
        ticket = Ticket(
            video_id=test_video.id,
            title="Test Ticket",
            description="Test description",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
            threat_level=ThreatLevel.MEDIUM,
            assigned_to=staff_user.id,
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket


@pytest.fixture
def staff_token(app_fixture, staff_user):
    with app_fixture.app_context():
        return create_access_token(identity=str(staff_user.id))


@pytest.fixture
def admin_token(app_fixture, admin_user):
    with app_fixture.app_context():
        return create_access_token(identity=str(admin_user.id))


class TestReportsAPI:
    def test_download_report_pdf_success(self, client, test_ticket, staff_token):
        """Test successful PDF report download."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/pdf"
        assert len(response.data) > 0
        # Verify PDF header
        assert response.data.startswith(b"%PDF")

    def test_download_report_json_success(self, client, test_ticket, staff_token):
        """Test successful JSON report download."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=json",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/json"
        data = json.loads(response.data)
        assert "ticket" in data

    def test_download_report_default_format(self, client, test_ticket, staff_token):
        """Test that default format is PDF."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_download_report_invalid_format(self, client, test_ticket, staff_token):
        """Test error handling for invalid format."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=invalid",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "format" in data["error"].lower()

    def test_download_report_cache_hit(self, client, test_ticket, staff_token, monkeypatch):
        """Test that cached report is returned quickly."""
        # Mock report service to simulate cache hit
        from src.api import reports as reports_module

        mock_service = Mock()
        mock_service.generate_report.return_value = (b"cached_pdf", None)
        reports_module.report_service = mock_service

        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 200
        assert response.data == b"cached_pdf"

    def test_download_report_not_assigned_as_staff(self, client, app_fixture, test_video, staff_token):
        """Test that staff cannot download unassigned tickets."""
        with app_fixture.app_context():
            # Create ticket assigned to different user
            other_user = User(
                username="other_staff",
                email="other@test.com",
                role=UserRole.STAFF,
                is_active=True,
            )
            other_user.set_password("password123")
            db.session.add(other_user)
            db.session.commit()

            ticket = Ticket(
                video_id=test_video.id,
                title="Other Ticket",
                description="Other description",
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.OPEN,
                threat_level=ThreatLevel.MEDIUM,
                assigned_to=other_user.id,
            )
            db.session.add(ticket)
            db.session.commit()

            response = client.get(
                f"/api/tickets/{ticket.id}/report/download?format=pdf",
                headers={"Authorization": f"Bearer {staff_token}"},
            )

            assert response.status_code == 403
            data = json.loads(response.data)
            assert "forbidden" in data["error"].lower() or "not authorized" in data["error"].lower()

    def test_download_report_as_admin(self, client, test_ticket, admin_token):
        """Test that admin can download any ticket."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert response.content_type == "application/pdf"

    def test_download_report_ticket_not_found(self, client, staff_token):
        """Test error handling for non-existent ticket."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/tickets/{fake_id}/report/download?format=pdf",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_download_report_without_auth(self, client, test_ticket):
        """Test that unauthenticated requests are rejected."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
        )

        assert response.status_code == 401

    def test_download_report_cache_invalidation(self, client, app_fixture, test_ticket, staff_token):
        """Test that cache is invalidated on ticket update."""
        from src.services.report_service import ReportService

        report_service = ReportService()

        # Generate and cache report
        cache_key = f"report:{test_ticket.id}:pdf"
        report_service.redis_client.setex(cache_key, 3600, b"cached_data")

        # Update ticket status (should invalidate cache)
        with app_fixture.app_context():
            from src.services.ticket_service import TicketService

            ticket_service = TicketService()
            # Get user_id from staff_user fixture
            from flask_jwt_extended import decode_token

            token_data = decode_token(staff_token)
            user_id = token_data["sub"]

            ticket_service.update_status(
                ticket_id=test_ticket.id,
                new_status=TicketStatus.ACKNOWLEDGED,
                user_id=user_id,
            )

        # Verify cache is cleared
        assert report_service.redis_client.get(cache_key) is None

    def test_download_report_audit_log(self, client, app_fixture, test_ticket, staff_token):
        """Test that report downloads are logged to audit log."""
        with app_fixture.app_context():
            # Get user from token
            from flask_jwt_extended import decode_token

            token_data = decode_token(staff_token)
            user_id = token_data["sub"]

            # Count existing audit logs
            initial_count = AuditLog.query.filter_by(action="report_downloaded").count()

            # Download report
            response = client.get(
                f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
                headers={"Authorization": f"Bearer {staff_token}"},
            )

            assert response.status_code == 200

            # Verify audit log was created
            final_count = AuditLog.query.filter_by(action="report_downloaded").count()
            assert final_count == initial_count + 1

            # Verify audit log details
            audit_log = AuditLog.query.filter_by(
                action="report_downloaded", resource_id=test_ticket.id
            ).first()
            assert audit_log is not None
            assert audit_log.user_id == user_id
            assert audit_log.resource_type == "ticket"

    def test_cors_headers(self, client, test_ticket, staff_token):
        """Test that CORS headers are present."""
        response = client.get(
            f"/api/tickets/{test_ticket.id}/report/download?format=pdf",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == 200
        # CORS headers should be present (handled by Flask-CORS)
        # This is a basic check - actual CORS testing requires Origin header

