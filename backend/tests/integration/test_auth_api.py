import os
from typing import Tuple

import pytest

from src.app import create_app, db
from src.models.audit_log import AuditLog
from src.models.session import Session
from src.models.user import User
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
    monkeypatch.setattr("src.services.auth_service.create_access_token", fake_create_access_token)
    monkeypatch.setattr("src.services.auth_service.create_refresh_token", fake_create_refresh_token)
    monkeypatch.setattr("src.services.auth_service.decode_token", fake_decode_token)

    from src.api import auth as auth_module

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


def signup_user(client, username: str, email: str, password: str) -> Tuple[int, dict]:
    response = client.post(
        "/api/auth/signup",
        json={"username": username, "email": email, "password": password},
    )
    return response.status_code, response.get_json()


def login_user(client, username: str, password: str) -> Tuple[int, dict]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    return response.status_code, response.get_json()


def test_signup_endpoint(client):
    status, data = signup_user(client, "user1", "user1@example.com", "Password123")
    assert status == 201
    assert data["user"]["username"] == "user1"
    assert User.query.filter_by(username="user1").first() is not None


def test_signup_duplicate_username(client):
    signup_user(client, "duplicate", "dup@example.com", "Password123")
    status, data = signup_user(client, "duplicate", "dup2@example.com", "Password123")
    assert status == 409
    assert "error" in data


def test_login_endpoint(client):
    signup_user(client, "loginapi", "loginapi@example.com", "Password123")
    status, data = login_user(client, "loginapi", "Password123")
    assert status == 200
    assert "access_token" in data and "refresh_token" in data
    assert Session.query.count() == 1


def test_login_invalid_credentials(client):
    signup_user(client, "badlogin", "badlogin@example.com", "Password123")
    status, data = login_user(client, "badlogin", "WrongPassword")
    assert status == 401
    assert "error" in data


def test_login_rate_limiting(client):
    signup_user(client, "ratelimit", "ratelimit@example.com", "Password123")
    for _ in range(5):
        status, _ = login_user(client, "ratelimit", "WrongPassword")
        assert status == 401
    status, data = login_user(client, "ratelimit", "WrongPassword")
    assert status == 429
    assert "error" in data


def test_refresh_token_endpoint(client):
    signup_user(client, "refreshapi", "refreshapi@example.com", "Password123")
    _, login_data = login_user(client, "refreshapi", "Password123")
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "access_token" in body and "refresh_token" in body


def test_logout_endpoint(client):
    signup_user(client, "logoutapi", "logoutapi@example.com", "Password123")
    _, login_data = login_user(client, "logoutapi", "Password123")
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert response.status_code == 200
    assert Session.query.filter_by(is_active=True).count() == 0


def test_logout_without_token(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 401


def test_promote_user_endpoint(client):
    signup_user(client, "adminuser", "adminuser@example.com", "Password123")
    admin = User.query.filter_by(username="adminuser").first()
    admin.role = "admin"
    db.session.commit()

    signup_user(client, "staffuser", "staffuser@example.com", "Password123")
    _, admin_login = login_user(client, "adminuser", "Password123")
    response = client.post(
        "/api/auth/promote-user",
        json={"user_id": User.query.filter_by(username="staffuser").first().id},
        headers={"Authorization": f"Bearer {admin_login['access_token']}"},
    )
    assert response.status_code == 200
    assert User.query.filter_by(username="staffuser").first().role == "admin"


def test_promote_user_without_admin(client):
    signup_user(client, "staff1", "staff1@example.com", "Password123")
    signup_user(client, "staff2", "staff2@example.com", "Password123")
    _, login_data = login_user(client, "staff1", "Password123")
    response = client.post(
        "/api/auth/promote-user",
        json={"user_id": User.query.filter_by(username="staff2").first().id},
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert response.status_code in (400, 403)


def test_demote_user_endpoint(client):
    signup_user(client, "makeadmin", "makeadmin@example.com", "Password123")
    admin_user = User.query.filter_by(username="makeadmin").first()
    admin_user.role = "admin"
    db.session.commit()

    _, login_data = login_user(client, "makeadmin", "Password123")
    response = client.post(
        "/api/auth/demote-user",
        json={"user_id": admin_user.id},
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert response.status_code == 200
    assert User.query.filter_by(username="makeadmin").first().role == "staff"


def test_get_me_endpoint(client):
    signup_user(client, "whoami", "whoami@example.com", "Password123")
    _, login_data = login_user(client, "whoami", "Password123")
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["username"] == "whoami"


def test_get_me_without_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_cors_headers(client):
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "Access-Control-Allow-Origin" in response.headers


def test_audit_logging(client):
    signup_user(client, "auditapi", "auditapi@example.com", "Password123")
    login_user(client, "auditapi", "Password123")
    logs = AuditLog.query.filter_by(action="login").all()
    assert len(logs) >= 1

