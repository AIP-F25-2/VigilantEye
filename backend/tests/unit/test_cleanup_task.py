import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pytest

from src.app import create_app, db
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.user import User
from src.models.video import Video
from src.services.storage_service import StorageService
from src.tasks import cleanup_task


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def hincrby(self, key: str, field: str, amount: int) -> None:
        data = self.store.setdefault(key, {})
        data[field] = int(data.get(field, 0)) + amount

    def hset(self, key: str, field: str | None = None, value: Any | None = None, mapping=None) -> None:
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

    def hget(self, key: str, field: str) -> Any:
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return data.get(field)
        return None

    def get(self, key: str) -> Any:
        return self.store.get(key)


@pytest.fixture(scope="module")
def app(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    storage_dir = tmp_path_factory.mktemp("cleanup-storage")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))
    monkeypatch.setenv("SUPPORTED_VIDEO_FORMATS", "mp4")
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
    monkeypatch.setattr("src.services.storage_service.redis.from_url", lambda *_args, **_kwargs: store)
    return store


@pytest.fixture
def storage_service(tmp_path, monkeypatch, fake_redis):
    StorageService._instance = None
    StorageService._initialized = False
    base_path = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_BASE_PATH", str(base_path))
    cleanup_task.storage_base_path = base_path
    cleanup_task.cleanup_batch_size = 2
    cleanup_task.config.CLEANUP_ENABLED = True
    service = StorageService()
    return service


def _create_user(email: str) -> User:
    user = User(username=email, email=email, role="staff", is_active=True)
    user.set_password("Password123")
    db.session.add(user)
    db.session.commit()
    return user


def _expire_video(video: Video) -> None:
    video.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.session.add(video)
    db.session.commit()


def _create_person(video_id: str | None = None, expires: bool = True) -> Person:
    person = Person(
        video_id=video_id,
        person_tracking_id="tracker",
        first_seen=datetime.utcnow() - timedelta(minutes=5),
        last_seen=datetime.utcnow() - timedelta(minutes=1),
    )
    if expires:
        person.set_person_ttl()
        person.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.session.add(person)
    db.session.commit()
    return person


def _create_ticket(video_id: str | None) -> Ticket:
    ticket = Ticket(
        video_id=video_id,
        title="Ticket",
        priority="medium",
        status="open",
    )
    ticket.auto_close_at = datetime.utcnow() - timedelta(minutes=1)
    db.session.add(ticket)
    db.session.commit()
    return ticket


def test_cleanup_expired_files_videos(app, storage_service, fake_redis):
    with app.app_context():
        user = _create_user("cleanup-video@example.com")
        video, _ = storage_service.save_video(
            _build_filestorage(b"video", "clip.mp4"),
            user.id,
        )
        _expire_video(video)
        metrics = cleanup_task.cleanup_expired_files()
        assert metrics["deleted_videos"] == 1
        refreshed = Video.query.get(video.id)
        assert refreshed.is_deleted is True


def test_cleanup_expired_files_persons(app, storage_service):
    with app.app_context():
        _create_person(expires=True)
        metrics = cleanup_task.cleanup_expired_files()
        assert metrics["deleted_persons"] >= 1


def test_cleanup_expired_files_batch_processing(app, storage_service):
    with app.app_context():
        user = _create_user("batch@example.com")
        videos = []
        for idx in range(5):
            video, _ = storage_service.save_video(
                _build_filestorage(f"video-{idx}".encode(), f"clip{idx}.mp4"),
                user.id,
            )
            _expire_video(video)
            videos.append(video)
        metrics = cleanup_task.cleanup_expired_files()
        assert metrics["deleted_videos"] == len(videos)


def test_cleanup_expired_files_missing_file(app, storage_service):
    with app.app_context():
        user = _create_user("missing@example.com")
        video, _ = storage_service.save_video(
            _build_filestorage(b"video", "clip.mp4"),
            user.id,
        )
        path = video.get_storage_path()
        os.remove(path)
        _expire_video(video)
        metrics = cleanup_task.cleanup_expired_files()
        assert metrics["deleted_videos"] == 1


def test_auto_close_tickets(app):
    cleanup_task.config.CLEANUP_ENABLED = True
    with app.app_context():
        ticket = _create_ticket(None)
        metrics = cleanup_task.auto_close_tickets()
        assert metrics["closed_tickets"] == 1
        refreshed = Ticket.query.get(ticket.id)
        assert refreshed.status == "closed"
        history = TicketHistory.query.filter_by(ticket_id=ticket.id).first()
        assert history is not None


def test_sync_quota_to_database(fake_redis):
    fake_redis.hset("quota:user:123", "used_bytes", 4096)
    result = cleanup_task.sync_quota_to_database()
    assert result["synced_users"] == 1


def _build_filestorage(data: bytes, filename: str):
    import io
    from werkzeug.datastructures import FileStorage

    return FileStorage(stream=io.BytesIO(data), filename=filename, content_length=len(data))


