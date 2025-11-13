"""Shared pytest fixtures for all tests."""

import os
from pathlib import Path
from typing import Dict

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import FileStorage

from src.app import create_app, db
from src.models.user import User


class FakeRedis:
    """Fake Redis implementation for testing."""

    def __init__(self) -> None:
        self.store: Dict[str, str] = {}
        self.hash_store: Dict[str, Dict[str, str]] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        """Set key with TTL."""
        self.store[key] = value

    def get(self, key: str) -> str | None:
        """Get value by key."""
        return self.store.get(key)

    def delete(self, *keys: str) -> int:
        """Delete keys."""
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
            if key in self.hash_store:
                del self.hash_store[key]
                deleted += 1
        return deleted

    def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Increment hash field."""
        if name not in self.hash_store:
            self.hash_store[name] = {}
        if key not in self.hash_store[name]:
            self.hash_store[name][key] = "0"
        current = int(self.hash_store[name][key])
        self.hash_store[name][key] = str(current + amount)
        return current + amount

    def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field."""
        if name not in self.hash_store:
            self.hash_store[name] = {}
        self.hash_store[name][key] = value
        return 1

    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        return self.hash_store.get(name, {})

    def hget(self, name: str, key: str) -> str | None:
        """Get hash field."""
        return self.hash_store.get(name, {}).get(key)

    def incrby(self, key: str, amount: int = 1) -> int:
        """Increment key."""
        current = int(self.store.get(key, "0"))
        self.store[key] = str(current + amount)
        return current + amount

    def keys(self, pattern: str = "*") -> list:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self.store.keys()) + list(self.hash_store.keys())
        # Simple pattern matching
        import fnmatch
        all_keys = list(self.store.keys()) + list(self.hash_store.keys())
        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    def exists(self, key: str) -> int:
        """Check if key exists."""
        return 1 if key in self.store or key in self.hash_store else 0

    def clear(self) -> None:
        """Clear all data."""
        self.store.clear()
        self.hash_store.clear()


@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing."""
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    test_app = create_app("development")
    test_app.config["TESTING"] = True
    test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def cleanup_db(app):
    """Clean up database after each test."""
    with app.app_context():
        yield
        # After test
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def fake_redis(monkeypatch):
    """Create fake Redis instance and monkeypatch all Redis imports."""
    fake = FakeRedis()

    # Monkeypatch all Redis imports
    monkeypatch.setattr("src.services.auth_service.redis.from_url", lambda *_, **__: fake)
    monkeypatch.setattr("src.services.storage_service.redis.from_url", lambda *_, **__: fake)
    monkeypatch.setattr("src.services.ticket_service.redis.from_url", lambda *_, **__: fake)
    monkeypatch.setattr("src.tasks.cleanup_task.redis_client", fake)

    return fake


@pytest.fixture
def client(app):
    """Create Flask test client."""
    with app.test_client() as testing_client:
        yield testing_client


@pytest.fixture
def test_user(app):
    """Create a test staff user."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com", role="staff", is_active=True)
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app):
    """Create a test admin user."""
    with app.app_context():
        user = User(username="admin", email="admin@example.com", role="admin", is_active=True)
        user.set_password("admin123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def auth_headers(app):
    """Helper function to create auth headers for a user."""

    def _auth_headers(user: User) -> Dict[str, str]:
        with app.app_context():
            token = create_access_token(identity=str(user.id))
            return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Create temporary storage directory structure."""
    storage_dir = tmp_path / "storage"
    (storage_dir / "videos").mkdir(parents=True)
    (storage_dir / "frames").mkdir(parents=True)
    (storage_dir / "audio").mkdir(parents=True)
    (storage_dir / "evidence").mkdir(parents=True)
    (storage_dir / "persons").mkdir(parents=True)
    (storage_dir / "reports").mkdir(parents=True)

    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))
    return storage_dir


# Helper functions
def create_user(username: str, email: str, password: str, role: str = "staff") -> User:
    """Create and persist a user."""
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_video(user_id: str, filename: str = "test.mp4", status: str = "ready"):
    """Create and persist a video."""
    from src.models.video import Video

    video = Video(
        filename=filename,
        filepath=f"videos/{filename}",
        user_id=user_id,
        upload_type="upload",
        status=status,
    )
    db.session.add(video)
    db.session.commit()
    return video


def create_ticket(video_id: str, priority: str = "medium", status: str = "open"):
    """Create and persist a ticket."""
    from src.models.ticket import Ticket

    ticket = Ticket(
        video_id=video_id,
        title="Test Ticket",
        description="Test description",
        priority=priority,
        status=status,
        threat_level=priority,
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket


def make_file_storage(data: bytes, filename: str) -> FileStorage:
    """Create Werkzeug FileStorage for upload tests."""
    from io import BytesIO

    return FileStorage(stream=BytesIO(data), filename=filename, content_type="video/mp4")
