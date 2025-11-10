import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pytest
from werkzeug.datastructures import FileStorage

from src.app import create_app, db
from src.models.audit_log import AuditLog
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.user import User
from src.models.video import Video
from src.services.storage_service import (
    QuotaExceededError,
    StorageError,
    StorageFileNotFoundError,
    StorageService,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def hincrby(self, key: str, field: str, amount: int) -> None:
        hash_map = self.store.setdefault(key, {})
        hash_map[field] = int(hash_map.get(field, 0)) + amount

    def hset(self, key: str, field: str | None = None, value: Any | None = None, mapping=None) -> None:
        hash_map = self.store.setdefault(key, {})
        if mapping:
            for k, v in mapping.items():
                hash_map[k] = v
        elif field:
            hash_map[field] = value

    def hgetall(self, key: str) -> Dict[str, Any]:
        value = self.store.get(key, {})
        return {k: str(v) for k, v in value.items()}

    def get(self, key: str) -> Any:
        value = self.store.get(key)
        if isinstance(value, dict):
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value

    def incrby(self, key: str, amount: int) -> None:
        self.store[key] = int(self.store.get(key, 0)) + amount

    def keys(self, pattern: str) -> list[str]:
        if pattern == "quota:user:*":
            return [k for k in self.store if k.startswith("quota:user:")]
        return []

    def hget(self, key: str, field: str) -> Any:
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return data.get(field)
        return None


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    storage_base = tmp_path_factory.mktemp("storage-service")
    os.environ["STORAGE_BASE_PATH"] = str(storage_base)
    os.environ["SUPPORTED_VIDEO_FORMATS"] = "mp4,avi,mov"
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
    monkeypatch.setattr("src.services.storage_service.redis.from_url", lambda *_args, **_kwargs: store)
    return store


def _reset_storage_service(monkeypatch, base_path: Path) -> StorageService:
    StorageService._instance = None
    StorageService._initialized = False
    monkeypatch.setenv("STORAGE_BASE_PATH", str(base_path))
    monkeypatch.setenv("SUPPORTED_VIDEO_FORMATS", "mp4,avi,mov")
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "5")
    monkeypatch.setenv("USER_QUOTA_MAX_GB", "10")
    service = StorageService()
    return service


def _create_user(email: str = "user@example.com") -> User:
    user = User(username=email, email=email, role="staff", is_active=True)
    user.set_password("Password123")
    db.session.add(user)
    db.session.commit()
    return user


def _create_ticket(video_id: str | None, assigned_to: str | None = None) -> Ticket:
    ticket = Ticket(
        video_id=video_id,
        title="Test Ticket",
        priority="medium",
        status="open",
        assigned_to=assigned_to,
    )
    ticket.set_auto_close_deadline()
    db.session.add(ticket)
    db.session.commit()
    return ticket


def _file_storage(data: bytes, filename: str) -> FileStorage:
    stream = io.BytesIO(data)
    return FileStorage(stream=stream, filename=filename, content_length=len(data))


def test_save_video_success(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "videos-success"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user()
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, error = storage_service.save_video(file_obj, user.id)
        assert error is None
        assert video is not None
        assert Path(video.get_storage_path()).exists()
        assert video.checksum is not None
        assert fake_redis.store[f"quota:user:{user.id}"]["used_bytes"] == len(b"video-bytes")
        logs = AuditLog.query.filter_by(action="video_uploaded").all()
        assert logs


def test_save_video_exceeds_size_limit(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "videos-too-large"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "0")
    StorageService._instance = None
    StorageService._initialized = False
    storage_service = StorageService()
    with app.app_context():
        user = _create_user("size@example.com")
        file_obj = _file_storage(b"x" * 1024, "large.mp4")
        video, error = storage_service.save_video(file_obj, user.id)
        assert video is None
        assert isinstance(error, QuotaExceededError)


def test_save_video_exceeds_user_quota(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "videos-quota"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("quota-limit@example.com")
        storage_service.config.USER_QUOTA_MAX_GB = 0  # type: ignore[attr-defined]
        file_obj = _file_storage(b"x" * 1024, "clip.mp4")
        video, error = storage_service.save_video(file_obj, user.id)
        assert video is None
        assert isinstance(error, QuotaExceededError)


def test_save_video_invalid_format(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "videos-invalid-format"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("format@example.com")
        file_obj = _file_storage(b"content", "video.exe")
        video, error = storage_service.save_video(file_obj, user.id)
        assert video is None
        assert isinstance(error, StorageError)


def test_save_video_rollback_on_db_error(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "videos-rollback"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("rollback@example.com")
        file_obj = _file_storage(b"content", "video.mp4")
        original_commit = db.session.commit

        def failing_commit():
            raise RuntimeError("DB error")

        monkeypatch.setattr(db.session, "commit", failing_commit)
        video, error = storage_service.save_video(file_obj, user.id)
        assert video is None
        assert error is not None
        assert not list(Path(base_path).rglob("*.mp4"))
        monkeypatch.setattr(db.session, "commit", original_commit)


def test_save_frame_success(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "frames-success"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("frame@example.com")
        file_obj = _file_storage(b"frame-video", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        frame_data = b"\x89PNG\r\n"
        evidence, error = storage_service.save_frame(
            frame_data,
            ticket_id="ticket123",
            video_id=video.id if video else None,
            timestamp=datetime.utcnow(),
            frame_number=1,
        )
        assert error is None
        assert evidence is not None
        assert Path(evidence.get_storage_path()).exists()


def test_save_audio_success(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "audio-success"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("audio@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        audio_data = b"RIFF....WAVE"
        evidence, error = storage_service.save_audio(
            audio_data,
            ticket_id="ticket-audio",
            video_id=video.id if video else None,
            timestamp=datetime.utcnow(),
        )
        assert error is None
        assert evidence is not None
        assert Path(evidence.get_storage_path()).exists()


def test_delete_video_success(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "delete-video"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("delete@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        assert video is not None
        success, error = storage_service.delete_file(video.id, "video", user.id, "cleanup")
        assert error is None
        assert success is True
        assert Video.query.get(video.id).is_deleted is True


def test_delete_video_with_dependencies(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "delete-dependency"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("dependency@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        ticket = _create_ticket(video_id=video.id)
        success, error = storage_service.delete_file(video.id, "video", user.id, "blocked")
        assert success is False
        assert isinstance(error, StorageError)
        assert "Cannot delete" in str(error)
        assert Ticket.query.get(ticket.id).status == "open"


def test_delete_file_not_found(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "delete-not-found"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        success, error = storage_service.delete_file("missing-id", "video", "admin")
        assert success is False
        assert isinstance(error, StorageError)


def test_get_file_path_success(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "path-success"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("path@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        filepath, error = storage_service.get_file_path(video.id, "video")
        assert error is None
        assert filepath and Path(filepath).exists()


def test_get_file_path_missing_on_disk(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "path-missing"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("missing@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        video, _ = storage_service.save_video(file_obj, user.id)
        os.remove(video.get_storage_path())
        filepath, error = storage_service.get_file_path(video.id, "video")
        assert filepath is None
        assert isinstance(error, StorageFileNotFoundError)


def test_get_user_quota_from_redis(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "quota-redis"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("quota@example.com")
        fake_redis.hset(f"quota:user:{user.id}", "used_bytes", 2048)
        quota, error = storage_service.get_user_quota(user.id)
        assert error is None
        assert quota["used_bytes"] == 2048


def test_get_user_quota_from_database(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "quota-db"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("dbquota@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        storage_service.save_video(file_obj, user.id)
        quota, error = storage_service.get_user_quota(user.id)
        assert error is None
        assert quota["used_bytes"] > 0
        assert f"quota:user:{user.id}" in fake_redis.store


def test_get_system_quota(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "system-quota"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        user = _create_user("system@example.com")
        file_obj = _file_storage(b"video-bytes", "clip.mp4")
        storage_service.save_video(file_obj, user.id)
        quota, error = storage_service.get_system_quota()
        assert error is None
        assert quota["used_bytes"] >= len(b"video-bytes")
        assert "breakdown" in quota


def test_calculate_checksum(app, tmp_path, fake_redis, monkeypatch):
    base_path = tmp_path / "checksum"
    storage_service = _reset_storage_service(monkeypatch, base_path)
    with app.app_context():
        file_obj = _file_storage(b"checksum", "clip.mp4")
        checksum, _ = storage_service._write_file_stream(file_obj, base_path / "test.mp4")  # type: ignore[attr-defined]
        assert checksum == "1f0b3f8cecf236503d1b47779fba399a097e68bc35cdbd22fcf04dc327f738e9"


