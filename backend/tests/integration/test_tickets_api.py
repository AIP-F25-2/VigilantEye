import os
from datetime import datetime, timedelta
from typing import Tuple

import pytest

from src.app import create_app, db
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel, UserRole
from src.models.evidence import Evidence
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.user import User
from src.models.video import Video
from src.services.auth_service import AuthService


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

    def fake_decode_token(token):
        parts = token.split("-")
        if len(parts) >= 3:
            return {"sub": parts[2], "jti": f"jti-{token}"}
        return {"sub": "", "jti": f"jti-{token}"}

    monkeypatch.setattr("src.services.auth_service.redis.from_url", lambda *_, **__: fake_redis)
    monkeypatch.setattr("src.services.ticket_service.redis.from_url", lambda *_, **__: fake_redis)
    monkeypatch.setattr("src.services.auth_service.create_access_token", fake_create_access_token)
    monkeypatch.setattr("src.services.auth_service.create_refresh_token", fake_create_refresh_token)
    monkeypatch.setattr("src.services.auth_service.decode_token", fake_decode_token)

    from src.api import auth as auth_module
    from src.api import tickets as tickets_module

    auth_module.auth_service = AuthService()
    auth_module.auth_service.redis_client = fake_redis

    test_app = create_app("development")
    test_app.config["TESTING"] = True

    with test_app.app_context():
        db.create_all()
        yield test_app, fake_redis, counters
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_fixture):
    app, _, _ = app_fixture
    with app.test_client() as testing_client:
        yield testing_client


@pytest.fixture(autouse=True)
def clean_database(app_fixture):
    app, fake_redis, counters = app_fixture
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    fake_redis.store.clear()
    counters["access"] = 0
    counters["refresh"] = 0


def login_user(client, username: str, password: str) -> Tuple[int, dict]:
    """Helper to login and get access token."""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        content_type="application/json",
    )
    data = response.get_json() if response.is_json else {}
    return response.status_code, data


def create_test_video(app, user_id: str = None) -> Video:
    """Helper to create test video."""
    with app.app_context():
        # Create a test user if not provided
        if user_id is None:
            user = User(username="test_user", email="test@test.com", role=UserRole.STAFF, is_active=True)
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            user_id = user.id
        
        video = Video(
            filename="test_video.mp4",
            filepath="/test/path/test_video.mp4",
            duration=100.0,
            status="ready",
            upload_type="upload",
            user_id=user_id,
        )
        db.session.add(video)
        db.session.commit()
        return video


def create_test_analysis_result(threat_level: str = "high") -> dict:
    """Helper to create AI analysis result dict."""
    return {
        "threat_level": threat_level,
        "reasoning": "Suspicious activity detected",
        "key_factors": ["weapon", "aggressive behavior"],
    }


def create_test_ticket(app, video_id: str, status: str = "open", assigned_to: str = None) -> Ticket:
    """Helper to create test ticket."""
    with app.app_context():
        ticket = Ticket(
            video_id=video_id,
            title="Test Ticket",
            description="Test description",
            priority=TicketPriority.MEDIUM,
            status=status,
            threat_level=ThreatLevel.HIGH,
            assigned_to=assigned_to,
        )
        ticket.set_auto_close_deadline()
        db.session.add(ticket)
        db.session.commit()
        return ticket


def test_create_ticket_success(client, app_fixture):
    """Test creating a ticket successfully."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff1", email="staff1@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff1", "password123")
        assert status_code == 200
        token = data.get("access_token")

        # Create video
        video = create_test_video(app, user.id)

        # Create ticket
        analysis_result = create_test_analysis_result()
        response = client.post(
            "/api/tickets",
            json={
                "video_id": video.id,
                "analysis_result": analysis_result,
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Ticket created successfully"
        assert "ticket" in data
        assert data["ticket"]["status"] == TicketStatus.OPEN

        # Verify ticket in database
        ticket = Ticket.query.filter(Ticket.title.contains("Suspicious Activity")).first()
        assert ticket is not None
        assert ticket.auto_close_at is not None


def test_create_ticket_with_evidence_and_persons(client, app_fixture):
    """Test creating a ticket with evidence and persons linked."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff2", email="staff2@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff2", "password123")
        token = data.get("access_token")

        # Create video
        video = create_test_video(app, user.id)

        # Create dummy ticket for evidence
        dummy_ticket = Ticket(
            video_id=video.id,
            title="Dummy",
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
        )
        db.session.add(dummy_ticket)
        db.session.flush()

        # Create evidence
        evidence = Evidence(
            video_id=video.id,
            ticket_id=dummy_ticket.id,
            type="frame",
            filepath="/test/path/frame.jpg",
            timestamp=datetime.utcnow(),
            frame_number=1,
        )
        db.session.add(evidence)

        # Create person
        person = Person(
            video_id=video.id,
            person_tracking_id="person_001",
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        db.session.add(person)
        db.session.commit()

        # Create ticket with evidence and persons
        analysis_result = create_test_analysis_result()
        response = client.post(
            "/api/tickets",
            json={
                "video_id": video.id,
                "analysis_result": analysis_result,
                "evidence_ids": [evidence.id],
                "person_ids": [person.id],
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 201

        # Verify evidence linked
        db.session.refresh(evidence)
        ticket = Ticket.query.filter(Ticket.title.contains("Suspicious Activity")).first()
        assert evidence.ticket_id == ticket.id


def test_create_ticket_without_auth(client):
    """Test creating a ticket without authentication."""
    response = client.post(
        "/api/tickets",
        json={"video_id": "test-id", "analysis_result": {}},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_ticket_video_not_found(client, app_fixture):
    """Test creating a ticket with nonexistent video."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff3", email="staff3@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff3", "password123")
        token = data.get("access_token")

        # Create ticket with nonexistent video
        analysis_result = create_test_analysis_result()
        response = client.post(
            "/api/tickets",
            json={
                "video_id": "nonexistent-video-id",
                "analysis_result": analysis_result,
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["error"].lower()


def test_list_tickets_as_staff(client, app_fixture):
    """Test listing tickets as staff user (sees only assigned)."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create users
        user1 = User(username="staff4", email="staff4@test.com", role=UserRole.STAFF, is_active=True)
        user1.set_password("password123")
        user2 = User(username="staff5", email="staff5@test.com", role=UserRole.STAFF, is_active=True)
        user2.set_password("password123")
        db.session.add_all([user1, user2])
        db.session.commit()

        # Create video
        video = create_test_video(app, user1.id)

        # Create tickets
        ticket1 = create_test_ticket(app, video.id, assigned_to=user1.id)
        ticket2 = create_test_ticket(app, video.id, assigned_to=user2.id)

        # Login as user1
        status_code, data = login_user(client, "staff4", "password123")
        token = data.get("access_token")

        # List tickets
        response = client.get(
            "/api/tickets",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["tickets"]) == 1
        assert data["tickets"][0]["id"] == ticket1.id


def test_list_tickets_as_admin(client, app_fixture):
    """Test listing tickets as admin (sees all)."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create admin user
        admin = User(username="admin1", email="admin1@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()

        # Create video
        video = create_test_video(app, admin.id)

        # Create multiple tickets
        ticket1 = create_test_ticket(app, video.id)
        ticket2 = create_test_ticket(app, video.id)

        # Login as admin
        status_code, data = login_user(client, "admin1", "password123")
        token = data.get("access_token")

        # List tickets
        response = client.get(
            "/api/tickets",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["tickets"]) >= 2


def test_list_tickets_with_filters(client, app_fixture):
    """Test listing tickets with filters."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create admin user
        admin = User(username="admin2", email="admin2@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()

        # Create video
        video = create_test_video(app, admin.id)

        # Create tickets with different statuses
        ticket1 = create_test_ticket(app, video.id, status=TicketStatus.OPEN)
        ticket2 = create_test_ticket(app, video.id, status=TicketStatus.ACKNOWLEDGED)

        # Login as admin
        status_code, data = login_user(client, "admin2", "password123")
        token = data.get("access_token")

        # List with status filter
        response = client.get(
            "/api/tickets?status=open",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert all(t["status"] == TicketStatus.OPEN for t in data["tickets"])


def test_list_tickets_pagination(client, app_fixture):
    """Test listing tickets with pagination."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create admin user
        admin = User(username="admin3", email="admin3@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add(admin)
        db.session.commit()

        # Create video
        video = create_test_video(app, admin.id)

        # Create multiple tickets
        for i in range(5):
            create_test_ticket(app, video.id)

        # Login as admin
        status_code, data = login_user(client, "admin3", "password123")
        token = data.get("access_token")

        # List with pagination
        response = client.get(
            "/api/tickets?page=1&per_page=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["tickets"]) == 2
        assert data["pagination"]["total"] >= 5
        assert data["pagination"]["pages"] >= 3


def test_get_ticket_details_success(client, app_fixture):
    """Test getting ticket details successfully."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff6", email="staff6@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff6", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id, assigned_to=user.id)

        # Get ticket details
        response = client.get(
            f"/api/tickets/{ticket.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "ticket" in data
        assert data["ticket"]["id"] == ticket.id
        assert "evidence" in data["ticket"]
        assert "persons_of_interest" in data["ticket"]
        assert "history" in data["ticket"]


def test_get_ticket_details_not_assigned_as_staff(client, app_fixture):
    """Test staff user cannot view unassigned ticket."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create users
        user1 = User(username="staff7", email="staff7@test.com", role=UserRole.STAFF, is_active=True)
        user1.set_password("password123")
        user2 = User(username="staff8", email="staff8@test.com", role=UserRole.STAFF, is_active=True)
        user2.set_password("password123")
        db.session.add_all([user1, user2])
        db.session.commit()

        # Create video and ticket assigned to user1
        video = create_test_video(app, user1.id)
        ticket = create_test_ticket(app, video.id, assigned_to=user1.id)

        # Login as user2
        status_code, data = login_user(client, "staff8", "password123")
        token = data.get("access_token")

        # Try to get ticket details
        response = client.get(
            f"/api/tickets/{ticket.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


def test_get_ticket_details_not_assigned_as_admin(client, app_fixture):
    """Test admin user can view any ticket."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create users
        staff = User(username="staff9", email="staff9@test.com", role=UserRole.STAFF, is_active=True)
        staff.set_password("password123")
        admin = User(username="admin4", email="admin4@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add_all([staff, admin])
        db.session.commit()

        # Create video and ticket assigned to staff
        video = create_test_video(app, staff.id)
        ticket = create_test_ticket(app, video.id, assigned_to=staff.id)

        # Login as admin
        status_code, data = login_user(client, "admin4", "password123")
        token = data.get("access_token")

        # Get ticket details
        response = client.get(
            f"/api/tickets/{ticket.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["ticket"]["id"] == ticket.id


def test_acknowledge_ticket_success(client, app_fixture):
    """Test acknowledging a ticket successfully."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff10", email="staff10@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff10", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.OPEN)

        # Acknowledge ticket
        response = client.post(
            f"/api/tickets/{ticket.id}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket acknowledged successfully"
        assert data["ticket"]["status"] == TicketStatus.ACKNOWLEDGED

        # Verify in database
        db.session.refresh(ticket)
        assert ticket.status == TicketStatus.ACKNOWLEDGED
        assert ticket.assigned_to == user.id


def test_acknowledge_ticket_already_acknowledged(client, app_fixture):
    """Test acknowledging an already acknowledged ticket."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff11", email="staff11@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff11", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.ACKNOWLEDGED, assigned_to=user.id)

        # Try to acknowledge again
        response = client.post(
            f"/api/tickets/{ticket.id}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "already" in data["error"].lower()


def test_close_ticket_success(client, app_fixture):
    """Test closing a ticket successfully."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff12", email="staff12@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff12", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.ACKNOWLEDGED, assigned_to=user.id)

        # Close ticket
        response = client.post(
            f"/api/tickets/{ticket.id}/close",
            json={"reason": "Issue resolved"},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket closed successfully"
        assert data["ticket"]["status"] == TicketStatus.CLOSED

        # Verify in database
        db.session.refresh(ticket)
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None


def test_close_ticket_already_closed(client, app_fixture):
    """Test closing an already closed ticket."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff13", email="staff13@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff13", "password123")
        token = data.get("access_token")

        # Create video and closed ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.CLOSED, assigned_to=user.id)

        # Try to close again
        response = client.post(
            f"/api/tickets/{ticket.id}/close",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "already" in data["error"].lower()


def test_escalate_ticket_success(client, app_fixture):
    """Test escalating a ticket successfully."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff14", email="staff14@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff14", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.OPEN)

        # Escalate ticket
        response = client.post(
            f"/api/tickets/{ticket.id}/escalate",
            json={"reason": "No response from first responders"},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket escalated successfully"
        assert data["ticket"]["escalated"] is True

        # Verify in database
        db.session.refresh(ticket)
        assert ticket.escalated is True
        assert ticket.escalation_count == 1


def test_update_status_valid_transition(client, app_fixture):
    """Test updating status with valid transition."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff15", email="staff15@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff15", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.OPEN)

        # Update status
        response = client.patch(
            f"/api/tickets/{ticket.id}/status",
            json={"status": TicketStatus.ACKNOWLEDGED},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket status updated successfully"
        assert data["ticket"]["status"] == TicketStatus.ACKNOWLEDGED


def test_update_status_invalid_transition(client, app_fixture):
    """Test updating status with invalid transition."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff16", email="staff16@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff16", "password123")
        token = data.get("access_token")

        # Create video and closed ticket
        video = create_test_video(app)
        ticket = create_test_ticket(app, video.id, status=TicketStatus.CLOSED)

        # Try to update status to OPEN (invalid)
        response = client.patch(
            f"/api/tickets/{ticket.id}/status",
            json={"status": TicketStatus.OPEN},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "invalid" in data["error"].lower()


def test_assign_ticket_to_self_as_staff(client, app_fixture):
    """Test staff user assigning ticket to themselves."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create user and login
        user = User(username="staff17", email="staff17@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        status_code, data = login_user(client, "staff17", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user.id)
        ticket = create_test_ticket(app, video.id)

        # Assign to self
        response = client.patch(
            f"/api/tickets/{ticket.id}/assign",
            json={"user_id": user.id},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket assigned successfully"

        # Verify in database
        db.session.refresh(ticket)
        assert ticket.assigned_to == user.id


def test_assign_ticket_to_other_as_staff(client, app_fixture):
    """Test staff user cannot assign ticket to other users."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create users
        user1 = User(username="staff18", email="staff18@test.com", role=UserRole.STAFF, is_active=True)
        user1.set_password("password123")
        user2 = User(username="staff19", email="staff19@test.com", role=UserRole.STAFF, is_active=True)
        user2.set_password("password123")
        db.session.add_all([user1, user2])
        db.session.commit()

        # Login as user1
        status_code, data = login_user(client, "staff18", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, user1.id)
        ticket = create_test_ticket(app, video.id)

        # Try to assign to user2
        response = client.patch(
            f"/api/tickets/{ticket.id}/assign",
            json={"user_id": user2.id},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 403
        data = response.get_json()
        assert "forbidden" in data["error"].lower()


def test_assign_ticket_to_other_as_admin(client, app_fixture):
    """Test admin user can assign ticket to anyone."""
    app, _, _ = app_fixture
    with app.app_context():
        # Create users
        staff = User(username="staff20", email="staff20@test.com", role=UserRole.STAFF, is_active=True)
        staff.set_password("password123")
        admin = User(username="admin5", email="admin5@test.com", role=UserRole.ADMIN, is_active=True)
        admin.set_password("password123")
        db.session.add_all([staff, admin])
        db.session.commit()

        # Login as admin
        status_code, data = login_user(client, "admin5", "password123")
        token = data.get("access_token")

        # Create video and ticket
        video = create_test_video(app, admin.id)
        ticket = create_test_ticket(app, video.id)

        # Assign to staff
        response = client.patch(
            f"/api/tickets/{ticket.id}/assign",
            json={"user_id": staff.id},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Ticket assigned successfully"

        # Verify in database
        db.session.refresh(ticket)
        assert ticket.assigned_to == staff.id

