import json
import os
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel, UserRole
from src.models.evidence import Evidence
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.user import User
from src.models.video import Video
from src.services.report_service import ReportError, ReportService


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
    monkeypatch.setattr("src.services.report_service.redis.from_url", lambda *_, **__: store)
    return store


@pytest.fixture
def report_service(fake_redis, monkeypatch):
    # Mock dependencies
    mock_ticket_service = Mock()
    mock_person_detector = Mock()
    mock_storage_service = Mock()

    service = ReportService()
    service.redis_client = fake_redis
    service.ticket_service = mock_ticket_service
    service.person_detector = mock_person_detector
    service.storage_service = mock_storage_service

    return service


@pytest.fixture
def test_ticket_data():
    return {
        "id": "test-ticket-id",
        "video_id": "test-video-id",
        "title": "Test Ticket",
        "description": "Test description",
        "priority": TicketPriority.MEDIUM,
        "status": TicketStatus.OPEN,
        "threat_level": ThreatLevel.MEDIUM,
        "assigned_to": None,
        "created_by": None,
        "acknowledged_at": None,
        "closed_at": None,
        "escalated": False,
        "escalation_count": 0,
        "escalation_sent_at": None,
        "sla_breach": False,
        "auto_close_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None,
        "evidence": [],
        "persons_of_interest": [],
        "history": [],
    }


class TestReportService:
    def test_generate_report_pdf_cache_hit(self, report_service, test_ticket_data):
        """Test that cached PDF is returned immediately."""
        ticket_id = "test-ticket-id"
        cache_key = f"report:{ticket_id}:pdf"
        cached_pdf = b"cached_pdf_bytes"

        # Set cache
        report_service.redis_client.setex(cache_key, 3600, cached_pdf)

        # Generate report (should hit cache)
        result, error = report_service.generate_report(
            ticket_id=ticket_id, format="pdf", user_id="user1", user_role="admin"
        )

        assert error is None
        assert result == cached_pdf

    def test_generate_report_pdf_cache_miss(self, report_service, test_ticket_data):
        """Test PDF generation and caching on cache miss."""
        ticket_id = "test-ticket-id"

        # Mock ticket service
        report_service.ticket_service.get_ticket_details.return_value = (test_ticket_data, None)

        # Mock PDF generation
        with patch.object(report_service, "_generate_pdf_report") as mock_pdf:
            mock_pdf.return_value = b"generated_pdf_bytes"

            result, error = report_service.generate_report(
                ticket_id=ticket_id, format="pdf", user_id="user1", user_role="admin"
            )

            assert error is None
            assert result == b"generated_pdf_bytes"

            # Verify cache was set
            cache_key = f"report:{ticket_id}:pdf"
            assert report_service.redis_client.get(cache_key) == b"generated_pdf_bytes"

    def test_generate_report_json_format(self, report_service, test_ticket_data):
        """Test JSON report generation."""
        ticket_id = "test-ticket-id"

        report_service.ticket_service.get_ticket_details.return_value = (test_ticket_data, None)

        result, error = report_service.generate_report(
            ticket_id=ticket_id, format="json", user_id="user1", user_role="admin"
        )

        assert error is None
        assert result is not None
        # Verify it's valid JSON
        json_data = json.loads(result.decode("utf-8"))
        assert "ticket" in json_data

    def test_generate_report_ticket_not_found(self, report_service):
        """Test error handling when ticket not found."""
        ticket_id = "non-existent"

        from src.services.ticket_service import TicketNotFoundError

        report_service.ticket_service.get_ticket_details.return_value = (
            None,
            TicketNotFoundError("Ticket not found"),
        )

        result, error = report_service.generate_report(
            ticket_id=ticket_id, format="pdf", user_id="user1", user_role="admin"
        )

        assert result is None
        assert error is not None
        assert "not found" in str(error).lower()

    def test_generate_report_not_authorized(self, report_service):
        """Test error handling when user not authorized."""
        ticket_id = "test-ticket-id"

        from src.services.ticket_service import TicketAuthorizationError

        report_service.ticket_service.get_ticket_details.return_value = (
            None,
            TicketAuthorizationError("Forbidden"),
        )

        result, error = report_service.generate_report(
            ticket_id=ticket_id, format="pdf", user_id="user1", user_role="staff"
        )

        assert result is None
        assert error is not None

    def test_get_similar_persons_success(self, report_service):
        """Test similar persons retrieval."""
        persons = [{"id": "person1"}, {"id": "person2"}]

        # Mock person detector
        report_service.person_detector.find_similar_persons.return_value = (
            [{"person": {"id": "similar1"}, "score": 0.95}],
            None,
        )

        result = report_service._get_similar_persons(persons)

        assert len(result) == 2
        assert result[0]["person"]["id"] == "person1"
        assert len(result[0]["similar_persons"]) == 1

    def test_parse_ai_analysis_success(self, report_service):
        """Test AI analysis parsing from evidence."""
        evidence_list = [
            {
                "ai_analysis": {
                    "scene": {"scene_type": "parking_lot", "lighting": "dark"},
                    "persons": [{"age_estimate": 30, "gender": "male"}],
                    "objects": [{"class_name": "knife", "confidence": 0.9}],
                    "transcription": {"text": "Help me"},
                    "audio_events": [{"event_type": "glass_breaking"}],
                    "llm_reasoning": {"reasoning": "Suspicious activity"},
                }
            }
        ]

        result = report_service._parse_ai_analysis(evidence_list)

        assert result["scene"]["scene_type"] == "parking_lot"
        assert len(result["persons"]) == 1
        assert len(result["objects"]) == 1
        assert result["transcription"]["text"] == "Help me"
        assert len(result["audio_events"]) == 1
        assert result["llm_reasoning"]["reasoning"] == "Suspicious activity"

    def test_generate_executive_summary(self, report_service):
        """Test executive summary generation."""
        ticket_dict = {
            "id": "test-ticket",
            "threat_level": ThreatLevel.HIGH,
            "priority": TicketPriority.HIGH,
            "status": TicketStatus.OPEN,
            "sla_breach": False,
            "created_at": datetime.utcnow().isoformat(),
            "acknowledged_at": (datetime.utcnow().replace(microsecond=0)).isoformat(),
            "evidence": [
                {
                    "ai_analysis": {
                        "llm_reasoning": {
                            "reasoning": "Test reasoning " * 20,  # Long text
                            "key_factors": ["factor1", "factor2", "factor3", "factor4"],
                        }
                    }
                }
            ],
            "persons_of_interest": [{"id": "person1"}],
        }

        result = report_service._generate_executive_summary(ticket_dict)

        assert result["threat_level"] == ThreatLevel.HIGH
        assert result["evidence_count"] == 1
        assert result["person_count"] == 1
        assert result["response_time_seconds"] is not None
        assert len(result["key_factors"]) <= 3  # Top 3 only

    def test_generate_pdf_report(self, report_service, test_ticket_data):
        """Test PDF report generation."""
        report_data = {
            "ticket": test_ticket_data,
            "evidence": [],
            "persons": [],
            "similar_persons": [],
            "history": [],
            "ai_analysis": {},
            "executive_summary": {
                "threat_level": ThreatLevel.MEDIUM,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.OPEN,
                "evidence_count": 0,
                "person_count": 0,
                "response_time_seconds": None,
                "resolution_time_seconds": None,
                "sla_breach": False,
                "llm_reasoning_summary": None,
                "key_factors": [],
            },
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": "user1",
        }

        result = report_service._generate_pdf_report(report_data)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Verify it's a valid PDF (starts with PDF header)
        assert result.startswith(b"%PDF")

    def test_generate_json_report(self, report_service, test_ticket_data):
        """Test JSON report generation."""
        report_data = {
            "ticket": test_ticket_data,
            "evidence": [],
            "persons": [],
            "similar_persons": [],
            "history": [],
            "ai_analysis": {},
            "executive_summary": {},
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": "user1",
        }

        result = report_service._generate_json_report(report_data)

        assert result is not None
        assert isinstance(result, str)
        # Verify it's valid JSON
        json_data = json.loads(result)
        assert "ticket" in json_data

    def test_invalidate_cache(self, report_service):
        """Test cache invalidation."""
        ticket_id = "test-ticket-id"
        cache_key_pdf = f"report:{ticket_id}:pdf"
        cache_key_json = f"report:{ticket_id}:json"

        # Set cache
        report_service.redis_client.setex(cache_key_pdf, 3600, b"pdf_data")
        report_service.redis_client.setex(cache_key_json, 3600, b"json_data")

        # Invalidate
        report_service.invalidate_cache(ticket_id)

        # Verify cache is cleared
        assert report_service.redis_client.get(cache_key_pdf) is None
        assert report_service.redis_client.get(cache_key_json) is None

    def test_generate_report_invalid_format(self, report_service, test_ticket_data):
        """Test error handling for invalid format."""
        ticket_id = "test-ticket-id"

        report_service.ticket_service.get_ticket_details.return_value = (test_ticket_data, None)

        result, error = report_service.generate_report(
            ticket_id=ticket_id, format="invalid", user_id="user1", user_role="admin"
        )

        assert result is None
        assert error is not None
        assert isinstance(error, ReportError)

