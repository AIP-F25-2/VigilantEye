import os
from datetime import datetime, timedelta
import pytest

from src.app import create_app, db
from src.models.audit_log import AuditLog
from src.models.session import Session
from src.models.user import User
from src.services.auth_service import AuthService, AuthenticationError, ValidationError


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
    monkeypatch.setattr("src.services.auth_service.redis.from_url", lambda *_, **__: store)
    return store


@pytest.fixture
def token_mocks(monkeypatch):
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
        raise AuthenticationError("Invalid token format")

    monkeypatch.setattr("src.services.auth_service.create_access_token", fake_create_access_token)
    monkeypatch.setattr("src.services.auth_service.create_refresh_token", fake_create_refresh_token)
    monkeypatch.setattr("src.services.auth_service.decode_token", fake_decode_token)
    return counters


@pytest.fixture
def auth_service(fake_redis, token_mocks):
    service = AuthService()
    service.redis_client = fake_redis
    return service


def create_user(username: str, email: str, password: str, role: str = "staff") -> User:
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_signup_success(auth_service, app):
    user, error = auth_service.signup("testuser", "test@example.com", "Password123")
    assert error is None
    assert user is not None
    assert user.password_hash != "Password123"
    assert user.role == "staff"
    assert User.query.count() == 1


def test_signup_duplicate_username(auth_service, app):
    auth_service.signup("duplicate", "dup@example.com", "Password123")
    user, error = auth_service.signup("duplicate", "another@example.com", "Password123")
    assert user is None
    assert isinstance(error, ValidationError)
    assert "already exists" in str(error).lower()


def test_signup_weak_password(auth_service, app):
    user, error = auth_service.signup("weakpass", "weak@example.com", "123")
    assert user is None
    assert isinstance(error, ValidationError)


def test_login_success(auth_service, app, fake_redis):
    create_user("loginuser", "login@example.com", "Password123")
    access, refresh, user, error = auth_service.login("loginuser", "Password123")
    assert error is None
    assert access and refresh
    assert fake_redis.exists(f"access_token:{access}") == 1
    assert fake_redis.exists(f"refresh_token:{refresh}") == 1
    session = Session.query.filter_by(user_id=user.id).first()
    assert session is not None
    assert user.last_login is not None


def test_login_invalid_password(auth_service, app):
    create_user("invalidpass", "invalid@example.com", "Password123")
    access, refresh, user, error = auth_service.login("invalidpass", "WrongPassword")
    assert access is None
    assert refresh is None
    assert user is None
    assert isinstance(error, AuthenticationError)


def test_login_inactive_user(auth_service, app):
    user = create_user("inactive", "inactive@example.com", "Password123")
    user.is_active = False
    db.session.commit()
    access, refresh, user_obj, error = auth_service.login("inactive", "Password123")
    assert access is None and refresh is None and user_obj is None
    assert isinstance(error, AuthenticationError)


def test_refresh_token_success(auth_service, app, fake_redis):
    user = create_user("refresher", "refresh@example.com", "Password123")
    access, refresh, _, _ = auth_service.login("refresher", "Password123")
    assert access and refresh
    new_access, new_refresh, refreshed_user, error = auth_service.refresh_token(refresh)
    assert error is None
    assert refreshed_user.id == user.id
    assert new_access != access
    assert fake_redis.exists(f"access_token:{new_access}") == 1
    assert fake_redis.exists(f"refresh_token:{new_refresh}") == 1


def test_refresh_token_expired(auth_service, app):
    new_access, new_refresh, user, error = auth_service.refresh_token("refresh-token-expired-1")
    assert new_access is None
    assert new_refresh is None
    assert user is None
    assert isinstance(error, AuthenticationError)


def test_logout_success(auth_service, app, fake_redis):
    create_user("logoutuser", "logout@example.com", "Password123")
    access, refresh, user, _ = auth_service.login("logoutuser", "Password123")
    fake_redis.setex(f"refresh_token:{refresh}", 10, user.id)
    success, error = auth_service.logout(access)
    assert success is True
    assert error is None
    assert fake_redis.exists(f"access_token:{access}") == 0


def test_promote_user_success(auth_service, app):
    staff_user = create_user("staff", "staff@example.com", "Password123")
    admin_user = create_user("admin", "admin@example.com", "Password123", role="admin")
    updated_user, error = auth_service.promote_user(staff_user.id, admin_user.id)
    assert error is None
    assert updated_user.role == "admin"


def test_promote_user_already_admin(auth_service, app):
    admin_user = create_user("alreadyadmin", "alreadyadmin@example.com", "Password123", role="admin")
    _, error = auth_service.promote_user(admin_user.id, admin_user.id)
    assert isinstance(error, ValidationError)
    assert "already" in str(error).lower()


def test_demote_user_success(auth_service, app):
    admin_user = create_user("demoteadmin", "demoteadmin@example.com", "Password123", role="admin")
    staff_user, error = auth_service.demote_user(admin_user.id, admin_user.id)
    assert error is None
    assert staff_user.role == "staff"


def test_validate_token_valid(auth_service, app, fake_redis):
    user = create_user("validtoken", "validtoken@example.com", "Password123")
    access, refresh, _, _ = auth_service.login("validtoken", "Password123")
    fake_redis.setex(f"access_token:{access}", 10, user.id)
    user_id = auth_service.validate_token(access)
    assert user_id == user.id


def test_validate_token_expired(auth_service, app):
    user = create_user("expiredtoken", "expiredtoken@example.com", "Password123")
    session = Session(
        user_id=user.id,
        access_token="expired-token",
        refresh_token="expired-refresh",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        refresh_expires_at=datetime.utcnow() - timedelta(hours=1),
        is_active=True,
    )
    db.session.add(session)
    db.session.commit()
    user_id = auth_service.validate_token("expired-token")
    assert user_id is None


def test_audit_logs_created(auth_service, app):
    auth_service.signup("audituser", "audit@example.com", "Password123")
    logs = AuditLog.query.filter_by(action="user_signup").all()
    assert len(logs) >= 1

