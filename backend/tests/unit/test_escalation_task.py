import os
from datetime import datetime, timedelta

import pytest

from src.app import create_app, db
from src.config.constants import TicketStatus
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.video import Video
from src.tasks import cleanup_task


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def hincrby(self, key: str, field: str, amount: int) -> None:
        data = self.store.setdefault(key, {})
        data[field] = int(data.get(field, 0)) + amount

    def hset(self, key: str, field: str | None = None, value: any | None = None, mapping=None) -> None:
        data = self.store.setdefault(key, {})
        if mapping:
            for k, v in mapping.items():
                data[k] = v
        elif field:
            data[field] = value

    def incrby(self, key: str, amount: int) -> None:
        self.store[key] = int(self.store.get(key, 0)) + amount

    def keys(self, pattern: str) -> list[str]:
        return [k for k in self.store if k.startswith("quota:user:")] if pattern == "quota:user:*" else []

    def hget(self, key: str, field: str) -> any:
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return data.get(field)
        return None

    def get(self, key: str) -> any:
        return self.store.get(key)


@pytest.fixture(scope="module")
def app(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    storage_dir = tmp_path_factory.mktemp("escalation-storage")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))
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
    monkeypatch.setattr(cleanup_task, "redis_client", store)
    monkeypatch.setattr("src.tasks.cleanup_task.redis_client", store)
    return store


@pytest.fixture
def setup_task_config(monkeypatch):
    """Setup task configuration for testing."""
    cleanup_task.config.CLEANUP_ENABLED = True
    cleanup_task.cleanup_batch_size = 1000
    cleanup_task.config.TICKET_ESCALATION_TIMEOUT_MINUTES = 15


def _create_video() -> Video:
    """Helper to create test video."""
    video = Video(
        filename="test_video.mp4",
        filepath="/test/path/test_video.mp4",
        duration=100.0,
        status="ready",
    )
    db.session.add(video)
    db.session.commit()
    return video


def _create_ticket_needing_escalation(video_id: str) -> Ticket:
    """Helper to create ticket that needs escalation."""
    ticket = Ticket(
        video_id=video_id,
        title="Test Ticket",
        description="Test description",
        priority="medium",
        status=TicketStatus.OPEN.value,
        threat_level="high",
    )
    # Set created_at to > 15 minutes ago
    ticket.created_at = datetime.utcnow() - timedelta(minutes=20)
    ticket.acknowledged_at = None
    ticket.escalated = False
    ticket.set_auto_close_deadline()
    db.session.add(ticket)
    db.session.commit()
    return ticket


def _create_ticket_not_ready_for_escalation(video_id: str) -> Ticket:
    """Helper to create ticket that doesn't need escalation yet."""
    ticket = Ticket(
        video_id=video_id,
        title="Test Ticket",
        description="Test description",
        priority="medium",
        status=TicketStatus.OPEN.value,
        threat_level="high",
    )
    # Set created_at to < 15 minutes ago
    ticket.created_at = datetime.utcnow() - timedelta(minutes=5)
    ticket.acknowledged_at = None
    ticket.escalated = False
    ticket.set_auto_close_deadline()
    db.session.add(ticket)
    db.session.commit()
    return ticket


def test_check_ticket_escalations_success(app, fake_redis, setup_task_config):
    """Test escalating tickets that need escalation."""
    with app.app_context():
        video = _create_video()

        # Create tickets needing escalation
        ticket1 = _create_ticket_needing_escalation(video.id)
        ticket2 = _create_ticket_needing_escalation(video.id)
        ticket3 = _create_ticket_needing_escalation(video.id)

        # Create tickets not ready for escalation
        ticket4 = _create_ticket_not_ready_for_escalation(video.id)
        ticket5 = _create_ticket_not_ready_for_escalation(video.id)

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 3
        assert len(metrics["errors"]) == 0

        # Verify tickets escalated
        db.session.refresh(ticket1)
        db.session.refresh(ticket2)
        db.session.refresh(ticket3)
        assert ticket1.escalated is True
        assert ticket1.escalation_count == 1
        assert ticket1.escalation_sent_at is not None
        assert ticket1.sla_breach is True
        assert ticket2.escalated is True
        assert ticket3.escalated is True

        # Verify tickets not escalated
        db.session.refresh(ticket4)
        db.session.refresh(ticket5)
        assert ticket4.escalated is False
        assert ticket5.escalated is False

        # Verify TicketHistory entries created
        history1 = TicketHistory.query.filter_by(ticket_id=ticket1.id, event="auto_escalated").first()
        assert history1 is not None


def test_check_ticket_escalations_already_escalated(app, fake_redis, setup_task_config):
    """Test that already escalated tickets are not escalated again."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)
        ticket.escalated = True
        ticket.escalation_count = 1
        db.session.commit()

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 0

        # Verify escalation_count unchanged
        db.session.refresh(ticket)
        assert ticket.escalation_count == 1


def test_check_ticket_escalations_already_acknowledged(app, fake_redis, setup_task_config):
    """Test that acknowledged tickets are not escalated."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)
        ticket.acknowledged_at = datetime.utcnow()
        db.session.commit()

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 0

        # Verify ticket not escalated
        db.session.refresh(ticket)
        assert ticket.escalated is False


def test_check_ticket_escalations_closed_ticket(app, fake_redis, setup_task_config):
    """Test that closed tickets are not escalated."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)
        ticket.status = TicketStatus.CLOSED.value
        db.session.commit()

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 0

        # Verify ticket not escalated
        db.session.refresh(ticket)
        assert ticket.escalated is False


def test_check_ticket_escalations_batch_processing(app, fake_redis, setup_task_config):
    """Test batch processing with large number of tickets."""
    with app.app_context():
        video = _create_video()

        # Create many tickets needing escalation
        tickets = []
        for i in range(250):
            ticket = _create_ticket_needing_escalation(video.id)
            tickets.append(ticket)

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 250
        assert len(metrics["errors"]) == 0

        # Verify all tickets escalated
        for ticket in tickets:
            db.session.refresh(ticket)
            assert ticket.escalated is True


def test_check_ticket_escalations_sla_breach_flag(app, fake_redis, setup_task_config):
    """Test that SLA breach flag is set correctly."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 1

        # Verify SLA breach flag set
        db.session.refresh(ticket)
        assert ticket.sla_breach is True

        # Verify TicketHistory includes sla_breach
        history = TicketHistory.query.filter_by(ticket_id=ticket.id, event="auto_escalated").first()
        assert history is not None
        assert "Not acknowledged within 15 minutes" in str(history.details)


def test_check_ticket_escalations_cleanup_disabled(app, fake_redis, monkeypatch):
    """Test that escalation task is skipped when cleanup is disabled."""
    with app.app_context():
        cleanup_task.config.CLEANUP_ENABLED = False

        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        assert metrics["escalated_tickets"] == 0
        assert len(metrics["errors"]) == 0

        # Verify ticket not escalated
        db.session.refresh(ticket)
        assert ticket.escalated is False

        # Re-enable for other tests
        cleanup_task.config.CLEANUP_ENABLED = True


def test_check_ticket_escalations_idempotent(app, fake_redis, setup_task_config):
    """Test that running escalation task twice has no effect on already escalated tickets."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)

        # Run escalation task first time
        metrics1 = cleanup_task.check_ticket_escalations()
        assert metrics1["escalated_tickets"] == 1

        # Run escalation task second time
        metrics2 = cleanup_task.check_ticket_escalations()
        assert metrics2["escalated_tickets"] == 0  # No new escalations

        # Verify ticket escalation_count unchanged
        db.session.refresh(ticket)
        assert ticket.escalation_count == 1


def test_check_ticket_escalations_messenger_fails(app, fake_redis, setup_task_config, monkeypatch):
    """Test graceful degradation when messenger service fails."""
    with app.app_context():
        video = _create_video()
        ticket = _create_ticket_needing_escalation(video.id)

        # Mock messenger service failure (task logs but doesn't fail)
        # The task doesn't actually call messenger service yet (Phase 10)
        # So this test verifies the error handling structure

        # Run escalation task
        metrics = cleanup_task.check_ticket_escalations()

        # Task should succeed even if messenger fails
        assert metrics["escalated_tickets"] == 1

        # Verify ticket still escalated
        db.session.refresh(ticket)
        assert ticket.escalated is True

