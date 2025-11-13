import os
from datetime import datetime, timedelta

import pytest

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel, UserRole
from src.models.audit_log import AuditLog
from src.models.evidence import Evidence
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.user import User
from src.models.video import Video
from src.services.ticket_service import (
    InvalidStateTransitionError,
    TicketAuthorizationError,
    TicketError,
    TicketNotFoundError,
    TicketService,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    def get(self, key: str) -> str | None:
        return self.store.get(key)


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
    monkeypatch.setattr("src.services.ticket_service.redis.from_url", lambda *_, **__: store)
    return store


@pytest.fixture
def ticket_service(fake_redis):
    service = TicketService()
    service.redis_client = fake_redis
    return service


@pytest.fixture
def staff_user(app):
    with app.app_context():
        user = User(username="staff1", email="staff1@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app):
    with app.app_context():
        user = User(username="admin1", email="admin1@test.com", role=UserRole.ADMIN, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_video(app, staff_user):
    with app.app_context():
        video = Video(
            filename="test_video.mp4",
            filepath="/test/path/test_video.mp4",
            duration=100.0,
            status="ready",
            upload_type="upload",
            user_id=staff_user.id,
        )
        db.session.add(video)
        db.session.commit()
        return video


@pytest.fixture
def test_evidence(app, test_video):
    with app.app_context():
        # Create a dummy ticket first since Evidence requires ticket_id
        dummy_ticket = Ticket(
            video_id=test_video.id,
            title="Dummy",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
        )
        db.session.add(dummy_ticket)
        db.session.flush()

        evidence = Evidence(
            video_id=test_video.id,
            ticket_id=dummy_ticket.id,
            type="frame",
            filepath="/test/path/frame.jpg",
            timestamp=datetime.utcnow(),
            frame_number=1,
        )
        db.session.add(evidence)
        db.session.commit()
        return evidence


@pytest.fixture
def test_person(app, test_video):
    with app.app_context():
        person = Person(
            video_id=test_video.id,
            person_tracking_id="person_001",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            age_estimate=30,
            gender="male",
        )
        db.session.add(person)
        db.session.commit()
        return person


def test_create_ticket_success(ticket_service, app, test_video, staff_user):
    """Test creating a ticket successfully."""
    with app.app_context():
        analysis_result = {
            "threat_level": "high",
            "reasoning": "Suspicious activity detected",
            "key_factors": ["weapon", "aggressive behavior"],
        }

        ticket, error = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
            created_by_user_id=staff_user.id,
        )

        assert error is None
        assert ticket is not None
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.threat_level == "high"
        assert ticket.auto_close_at is not None

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="created").first()
        assert history is not None

        # Check AuditLog entry
        audit = AuditLog.query.filter_by(action="ticket_created", resource_id=ticket.id).first()
        assert audit is not None


def test_create_ticket_with_evidence(ticket_service, app, test_video, test_evidence, staff_user):
    """Test creating a ticket with evidence linked."""
    with app.app_context():
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}

        ticket, error = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
            evidence_ids=[test_evidence.id],
            created_by_user_id=staff_user.id,
        )

        assert error is None
        assert ticket is not None

        # Refresh evidence from DB
        db.session.refresh(test_evidence)
        assert test_evidence.ticket_id == ticket.id
        assert test_evidence.expires_at is None  # TTL cleared


def test_create_ticket_with_persons(ticket_service, app, test_video, test_person, staff_user):
    """Test creating a ticket with persons linked."""
    with app.app_context():
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}

        ticket, error = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
            person_ids=[test_person.id],
            created_by_user_id=staff_user.id,
        )

        assert error is None
        assert ticket is not None
        assert len(ticket.persons_of_interest) == 1
        assert ticket.persons_of_interest[0].id == test_person.id


def test_create_ticket_video_not_found(ticket_service, app):
    """Test creating a ticket with nonexistent video."""
    with app.app_context():
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}

        ticket, error = ticket_service.create_ticket(
            video_id="nonexistent-video-id",
            analysis_result=analysis_result,
        )

        assert ticket is None
        assert error is not None
        assert isinstance(error, TicketNotFoundError)


def test_acknowledge_ticket_success(ticket_service, app, test_video, staff_user):
    """Test acknowledging a ticket successfully."""
    with app.app_context():
        # Create ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Acknowledge ticket
        ticket, error = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        assert error is None
        assert ticket.status == TicketStatus.ACKNOWLEDGED
        assert ticket.acknowledged_at is not None
        assert ticket.assigned_to == staff_user.id

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="acknowledged").first()
        assert history is not None


def test_acknowledge_ticket_sla_breach(ticket_service, app, test_video):
    """Test acknowledging a ticket that breached SLA."""
    with app.app_context():
        # Create ticket with old timestamp
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Manually set created_at to > 15 minutes ago
        ticket.created_at = datetime.utcnow() - timedelta(minutes=20)
        db.session.commit()

        # Create staff user
        user = User(username="staff2", email="staff2@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        # Acknowledge ticket
        ticket, error = ticket_service.acknowledge_ticket(ticket.id, user.id)

        assert error is None
        assert ticket.sla_breach is True


def test_acknowledge_ticket_already_acknowledged(ticket_service, app, test_video, staff_user):
    """Test acknowledging an already acknowledged ticket."""
    with app.app_context():
        # Create and acknowledge ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Try to acknowledge again
        ticket, error = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        assert ticket is None
        assert error is not None
        assert isinstance(error, TicketError)


def test_close_ticket_success(ticket_service, app, test_video, staff_user):
    """Test closing a ticket successfully."""
    with app.app_context():
        # Create and acknowledge ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Close ticket
        ticket, error = ticket_service.close_ticket(ticket.id, staff_user.id, reason="Issue resolved")

        assert error is None
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="closed").first()
        assert history is not None
        assert "Issue resolved" in str(history.details)


def test_close_ticket_already_closed(ticket_service, app, test_video, staff_user):
    """Test closing an already closed ticket."""
    with app.app_context():
        # Create and close ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.close_ticket(ticket.id, staff_user.id)

        # Try to close again
        ticket, error = ticket_service.close_ticket(ticket.id, staff_user.id)

        assert ticket is None
        assert error is not None
        assert isinstance(error, TicketError)


def test_escalate_ticket_success(ticket_service, app, test_video):
    """Test escalating a ticket successfully."""
    with app.app_context():
        # Create ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Escalate ticket
        ticket, error = ticket_service.escalate_ticket(ticket.id, reason="Manual escalation")

        assert error is None
        assert ticket.escalated is True
        assert ticket.escalation_count == 1
        assert ticket.escalation_sent_at is not None

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="escalated").first()
        assert history is not None


def test_escalate_ticket_messenger_fails(ticket_service, app, test_video, monkeypatch):
    """Test escalation when messenger service fails (graceful degradation)."""
    with app.app_context():
        # Create ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Mock messenger service to raise exception
        class MockMessenger:
            def send_escalation_alert(self, ticket):
                raise Exception("Messenger service unavailable")

        ticket_service.messenger_service = MockMessenger()

        # Escalate ticket (should succeed despite messenger failure)
        ticket, error = ticket_service.escalate_ticket(ticket.id)

        assert error is None
        assert ticket.escalated is True  # Ticket still escalated


def test_get_ticket_details_success(ticket_service, app, test_video, staff_user):
    """Test getting ticket details successfully."""
    with app.app_context():
        # Create ticket with evidence and persons
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Get ticket details
        ticket_dict, error = ticket_service.get_ticket_details(
            ticket_id=ticket.id, user_id=staff_user.id, user_role=staff_user.role
        )

        assert error is None
        assert ticket_dict is not None
        assert ticket_dict["id"] == ticket.id
        assert ticket_dict["status"] == TicketStatus.ACKNOWLEDGED
        assert "evidence" in ticket_dict
        assert "persons_of_interest" in ticket_dict
        assert "history" in ticket_dict


def test_get_ticket_details_not_found(ticket_service, app, staff_user):
    """Test getting details for nonexistent ticket."""
    with app.app_context():
        ticket_dict, error = ticket_service.get_ticket_details(
            ticket_id="nonexistent-id", user_id=staff_user.id, user_role=staff_user.role
        )

        assert ticket_dict is None
        assert error is not None
        assert isinstance(error, TicketNotFoundError)


def test_get_ticket_details_authorization_staff(ticket_service, app, test_video, staff_user):
    """Test staff user can only view assigned tickets."""
    with app.app_context():
        # Create ticket assigned to staff_user
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Create another staff user
        user2 = User(username="staff3", email="staff3@test.com", role=UserRole.STAFF, is_active=True)
        user2.set_password("password123")
        db.session.add(user2)
        db.session.commit()

        # Try to get ticket details as different user
        ticket_dict, error = ticket_service.get_ticket_details(
            ticket_id=ticket.id, user_id=user2.id, user_role=user2.role
        )

        assert ticket_dict is None
        assert error is not None
        assert isinstance(error, TicketAuthorizationError)


def test_get_ticket_details_authorization_admin(ticket_service, app, test_video, staff_user, admin_user):
    """Test admin user can view any ticket."""
    with app.app_context():
        # Create ticket assigned to staff_user
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Get ticket details as admin
        ticket_dict, error = ticket_service.get_ticket_details(
            ticket_id=ticket.id, user_id=admin_user.id, user_role=admin_user.role
        )

        assert error is None
        assert ticket_dict is not None
        assert ticket_dict["id"] == ticket.id


def test_list_tickets_staff_sees_assigned_only(ticket_service, app, test_video, staff_user):
    """Test staff user sees only assigned tickets."""
    with app.app_context():
        # Create multiple tickets
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket1, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket2, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Assign ticket1 to staff_user
        ticket1, _ = ticket_service.acknowledge_ticket(ticket1.id, staff_user.id)

        # Create another staff user
        user2 = User(username="staff4", email="staff4@test.com", role=UserRole.STAFF, is_active=True)
        user2.set_password("password123")
        db.session.add(user2)
        db.session.commit()

        # Assign ticket2 to user2
        ticket2, _ = ticket_service.acknowledge_ticket(ticket2.id, user2.id)

        # List tickets as staff_user
        result, error = ticket_service.list_tickets(
            filters=None, page=1, per_page=20, user_id=staff_user.id, user_role=staff_user.role
        )

        assert error is None
        assert result is not None
        assert len(result["tickets"]) == 1
        assert result["tickets"][0]["id"] == ticket1.id


def test_list_tickets_admin_sees_all(ticket_service, app, test_video, admin_user):
    """Test admin user sees all tickets."""
    with app.app_context():
        # Create multiple tickets
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket1, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket2, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # List tickets as admin
        result, error = ticket_service.list_tickets(
            filters=None, page=1, per_page=20, user_id=admin_user.id, user_role=admin_user.role
        )

        assert error is None
        assert result is not None
        assert len(result["tickets"]) >= 2


def test_list_tickets_with_filters(ticket_service, app, test_video):
    """Test listing tickets with filters."""
    with app.app_context():
        # Create tickets with different statuses
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket1, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Create admin user
        admin = User(username="admin2", email="admin2@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()

        # List with status filter
        result, error = ticket_service.list_tickets(
            filters={"status": TicketStatus.OPEN},
            page=1,
            per_page=20,
            user_id=admin.id,
            user_role=admin.role,
        )

        assert error is None
        assert result is not None
        assert all(t["status"] == TicketStatus.OPEN for t in result["tickets"])


def test_list_tickets_pagination(ticket_service, app, test_video, admin_user):
    """Test listing tickets with pagination."""
    with app.app_context():
        # Create multiple tickets
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        for i in range(5):
            ticket_service.create_ticket(
                video_id=test_video.id,
                analysis_result=analysis_result,
            )

        # List with pagination
        result, error = ticket_service.list_tickets(
            filters=None, page=1, per_page=2, user_id=admin_user.id, user_role=admin_user.role
        )

        assert error is None
        assert result is not None
        assert len(result["tickets"]) == 2
        assert result["pagination"]["total"] >= 5
        assert result["pagination"]["pages"] >= 3


def test_assign_ticket_success(ticket_service, app, test_video, staff_user, admin_user):
    """Test assigning a ticket successfully."""
    with app.app_context():
        # Create ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )

        # Assign ticket
        ticket, error = ticket_service.assign_ticket(
            ticket_id=ticket.id, user_id=staff_user.id, assigned_by_user_id=admin_user.id
        )

        assert error is None
        assert ticket.assigned_to == staff_user.id

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="assigned").first()
        assert history is not None


def test_update_status_valid_transition(ticket_service, app, test_video, staff_user):
    """Test updating status with valid transition."""
    with app.app_context():
        # Create and acknowledge ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.acknowledge_ticket(ticket.id, staff_user.id)

        # Update status to IN_PROGRESS
        ticket, error = ticket_service.update_status(
            ticket_id=ticket.id, new_status=TicketStatus.IN_PROGRESS, user_id=staff_user.id
        )

        assert error is None
        assert ticket.status == TicketStatus.IN_PROGRESS

        # Check TicketHistory entry
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="status_changed").first()
        assert history is not None


def test_update_status_invalid_transition(ticket_service, app, test_video, staff_user):
    """Test updating status with invalid transition."""
    with app.app_context():
        # Create and close ticket
        analysis_result = {"threat_level": "medium", "reasoning": "Test"}
        ticket, _ = ticket_service.create_ticket(
            video_id=test_video.id,
            analysis_result=analysis_result,
        )
        ticket, _ = ticket_service.close_ticket(ticket.id, staff_user.id)

        # Try to update status to OPEN (invalid transition)
        ticket, error = ticket_service.update_status(
            ticket_id=ticket.id, new_status=TicketStatus.OPEN, user_id=staff_user.id
        )

        assert ticket is None
        assert error is not None
        assert isinstance(error, InvalidStateTransitionError)


def test_validate_state_transition_valid(ticket_service):
    """Test all valid state transitions."""
    assert ticket_service._validate_state_transition(
        TicketStatus.OPEN, TicketStatus.ACKNOWLEDGED
    )
    assert ticket_service._validate_state_transition(TicketStatus.OPEN, TicketStatus.CLOSED)
    assert ticket_service._validate_state_transition(
        TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS
    )
    assert ticket_service._validate_state_transition(
        TicketStatus.ACKNOWLEDGED, TicketStatus.CLOSED
    )
    assert ticket_service._validate_state_transition(
        TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED
    )
    assert ticket_service._validate_state_transition(
        TicketStatus.IN_PROGRESS, TicketStatus.CLOSED
    )
    assert ticket_service._validate_state_transition(
        TicketStatus.RESOLVED, TicketStatus.CLOSED
    )


def test_validate_state_transition_invalid(ticket_service):
    """Test invalid state transitions."""
    # Cannot transition from CLOSED
    assert not ticket_service._validate_state_transition(
        TicketStatus.CLOSED, TicketStatus.OPEN
    )

    # Cannot un-acknowledge
    assert not ticket_service._validate_state_transition(
        TicketStatus.ACKNOWLEDGED, TicketStatus.OPEN
    )

    # Cannot go backward
    assert not ticket_service._validate_state_transition(
        TicketStatus.RESOLVED, TicketStatus.OPEN
    )
    assert not ticket_service._validate_state_transition(
        TicketStatus.IN_PROGRESS, TicketStatus.OPEN
    )

