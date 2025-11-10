import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import FileStorage

from src.app import create_app, db
from src.models.ticket import Ticket
from src.models.user import User
from src.models.video import Video
from src.services.storage_service import StorageService
from src.tasks import cleanup_task


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

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

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value

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
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
        return {}

    def incrby(self, key: str, amount: int) -> None:
        self.store[key] = int(self.store.get(key, 0)) + amount

    def keys(self, pattern: str) -> list[str]:
        return [k for k in self.store if k.startswith("quota:user:")] if pattern == "quota:user:*" else []

    def hget(self, key: str, field: str) -> Any:
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return data.get(field)
        return None


@pytest.fixture(scope="session")
def app_fixture(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("JWT_SECRET_KEY", "jwt-secret")
    storage_dir = tmp_path_factory.mktemp("storage-api")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))
    monkeypatch.setenv("SUPPORTED_VIDEO_FORMATS", "mp4")
    fake_redis = FakeRedis()

    monkeypatch.setattr("src.services.auth_service.redis.from_url", lambda *_args, **_kwargs: fake_redis)
    monkeypatch.setattr("src.services.storage_service.redis.from_url", lambda *_args, **_kwargs: fake_redis)
    monkeypatch.setattr("src.tasks.cleanup_task.redis_client", fake_redis, raising=False)
    cleanup_task.config.CLEANUP_ENABLED = True
    cleanup_task.storage_base_path = Path(storage_dir)

    from src.api import storage as storage_module

    StorageService._instance = None
    StorageService._initialized = False
    storage_service = StorageService()
    storage_module.storage_service = storage_service

    test_app = create_app("development")
    test_app.config["TESTING"] = True
    test_app.config["JWT_TOKEN_LOCATION"] = ["headers"]

    with test_app.app_context():
        db.create_all()
        yield test_app, storage_service, fake_redis, storage_dir, storage_module
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_fixture):
    app, _, _, _, _ = app_fixture
    with app.test_client() as testing_client:
        yield testing_client


@pytest.fixture(autouse=True)
def clean_state(app_fixture):
    app, _, fake_redis, storage_dir, _ = app_fixture
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    fake_redis.store.clear()
    for path in Path(storage_dir).rglob("*"):
        if path.is_file():
            path.unlink()
    yield
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    fake_redis.store.clear()


def create_user(username: str, email: str, password: str = "Password123", role: str = "staff") -> User:
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login_token(user: User) -> str:
    token = create_access_token(identity=user)
    return token


def upload_video(storage_service: StorageService, user: User, filename: str = "clip.mp4") -> Video:
    data = io.BytesIO(b"video-bytes")
    file_storage = FileStorage(stream=data, filename=filename, content_length=len(b"video-bytes"))
    video, error = storage_service.save_video(file_storage, user.id)
    assert error is None
    return video


def create_ticket(video: Video | None, assigned_to: User | None = None) -> Ticket:
    ticket = Ticket(
        video_id=video.id if video else None,
        title="Ticket",
        priority="medium",
        status="open",
        assigned_to=assigned_to.id if assigned_to else None,
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket


def build_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_delete_video_as_admin(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("admin", "admin@example.com", role="admin")
        user = create_user("staff", "staff@example.com")
        video = upload_video(storage_service, user)
        headers = build_headers(login_token(admin))
    response = client.delete(f"/api/storage/videos/{video.id}", headers=headers, json={"reason": "Cleanup"})
    assert response.status_code == 200
    with app.app_context():
        assert Video.query.get(video.id).is_deleted is True


def test_delete_video_as_staff(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        staff = create_user("staff1", "staff1@example.com")
        video = upload_video(storage_service, staff)
        headers = build_headers(login_token(staff))
    response = client.delete(f"/api/storage/videos/{video.id}", headers=headers)
    assert response.status_code == 403


def test_delete_video_with_open_ticket(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("admin2", "admin2@example.com", role="admin")
        staff = create_user("staff2", "staff2@example.com")
        video = upload_video(storage_service, staff)
        create_ticket(video)
        headers = build_headers(login_token(admin))
    response = client.delete(f"/api/storage/videos/{video.id}", headers=headers)
    assert response.status_code == 409


def test_delete_video_not_found(app_fixture, client):
    app, _, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("admin3", "admin3@example.com", role="admin")
        headers = build_headers(login_token(admin))
    response = client.delete("/api/storage/videos/00000000-0000-0000-0000-000000000000", headers=headers)
    assert response.status_code == 404


def test_delete_evidence_as_admin(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("admin4", "admin4@example.com", role="admin")
        staff = create_user("staff4", "staff4@example.com")
        video = upload_video(storage_service, staff)
        ticket = create_ticket(video)
        evidence, error = storage_service.save_frame(
            b"frame-data",
            ticket_id=ticket.id,
            video_id=video.id,
            timestamp=datetime.utcnow(),
            frame_number=1,
        )
        assert error is None
        headers = build_headers(login_token(admin))
    response = client.delete(
        f"/api/storage/evidence/{evidence.id}",
        headers=headers,
        json={"reason": "Legal"},
    )
    assert response.status_code == 409


def test_get_user_quota_own(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("quota", "quota@example.com")
        upload_video(storage_service, user)
        headers = build_headers(login_token(user))
    response = client.get(f"/api/storage/quota/user/{user.id}", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert "used_bytes" in body


def test_get_user_quota_other_as_staff(app_fixture, client):
    app, _, _, _, _ = app_fixture
    with app.app_context():
        user1 = create_user("quota1", "quota1@example.com")
        user2 = create_user("quota2", "quota2@example.com")
        headers = build_headers(login_token(user1))
    response = client.get(f"/api/storage/quota/user/{user2.id}", headers=headers)
    assert response.status_code == 403


def test_get_user_quota_other_as_admin(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("quota-admin", "quota-admin@example.com", role="admin")
        staff = create_user("quota-staff", "quota-staff@example.com")
        upload_video(storage_service, staff)
        headers = build_headers(login_token(admin))
    response = client.get(f"/api/storage/quota/user/{staff.id}", headers=headers)
    assert response.status_code == 200


def test_get_system_quota_as_admin(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("system-admin", "system-admin@example.com", role="admin")
        upload_video(storage_service, admin)
        headers = build_headers(login_token(admin))
    response = client.get("/api/storage/quota/system", headers=headers)
    assert response.status_code == 200
    assert "used_bytes" in response.get_json()


def test_get_system_quota_as_staff(app_fixture, client):
    app, _, _, _, _ = app_fixture
    with app.app_context():
        staff = create_user("system-staff", "system-staff@example.com")
        headers = build_headers(login_token(staff))
    response = client.get("/api/storage/quota/system", headers=headers)
    assert response.status_code == 403


def test_download_video_own(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("download", "download@example.com")
        video = upload_video(storage_service, user)
        headers = build_headers(login_token(user))
    response = client.get(f"/api/storage/videos/{video.id}/download", headers=headers)
    assert response.status_code == 200
    assert response.data


def test_download_video_other_as_staff(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        owner = create_user("owner", "owner@example.com")
        other = create_user("other", "other@example.com")
        video = upload_video(storage_service, owner)
        headers = build_headers(login_token(other))
    response = client.get(f"/api/storage/videos/{video.id}/download", headers=headers)
    assert response.status_code == 403


def test_download_video_other_as_admin(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        owner = create_user("owner2", "owner2@example.com")
        admin = create_user("admin-download", "admindownload@example.com", role="admin")
        video = upload_video(storage_service, owner)
        headers = build_headers(login_token(admin))
    response = client.get(f"/api/storage/videos/{video.id}/download", headers=headers)
    assert response.status_code == 200


def test_download_evidence(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("evidence-user", "evidence@example.com")
        video = upload_video(storage_service, user)
        ticket = create_ticket(video, assigned_to=user)
        evidence, error = storage_service.save_audio(
            b"audio-bytes",
            ticket_id=ticket.id,
            video_id=video.id,
            timestamp=datetime.utcnow(),
        )
        assert error is None
        headers = build_headers(login_token(user))
    response = client.get(f"/api/storage/evidence/{evidence.id}/download", headers=headers)
    assert response.status_code == 200


def test_download_evidence_not_assigned(app_fixture, client):
    app, storage_service, _, _, _ = app_fixture
    with app.app_context():
        owner = create_user("evidence-owner", "evidence-owner@example.com")
        other = create_user("evidence-other", "evidence-other@example.com")
        video = upload_video(storage_service, owner)
        ticket = create_ticket(video, assigned_to=owner)
        evidence, error = storage_service.save_frame(
            b"frame",
            ticket_id=ticket.id,
            video_id=video.id,
            timestamp=datetime.utcnow(),
            frame_number=1,
        )
        assert error is None
        headers = build_headers(login_token(other))
    response = client.get(f"/api/storage/evidence/{evidence.id}/download", headers=headers)
    assert response.status_code == 403


def test_trigger_cleanup_as_admin(app_fixture, client, monkeypatch):
    app, _, _, _, storage_module = app_fixture
    with app.app_context():
        admin = create_user("cleanup-admin", "cleanup-admin@example.com", role="admin")
        headers = build_headers(login_token(admin))

    class DummyTask:
        def __init__(self) -> None:
            self.id = "task-123"

    monkeypatch.setattr(storage_module.cleanup_expired_files, "delay", lambda: DummyTask())
    response = client.post("/api/storage/cleanup/trigger", headers=headers)
    assert response.status_code == 202
    assert "task_id" in response.get_json()


def test_trigger_cleanup_as_staff(app_fixture, client):
    app, _, _, _, _ = app_fixture
    with app.app_context():
        staff = create_user("cleanup-staff", "cleanup-staff@example.com")
        headers = build_headers(login_token(staff))
    response = client.post("/api/storage/cleanup/trigger", headers=headers)
    assert response.status_code == 403


def test_cors_headers(client):
    response = client.options(
        "/api/storage/videos/00000000-0000-0000-0000-000000000000",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert "Access-Control-Allow-Origin" in response.headers


def test_invalid_uuid_format(app_fixture, client):
    app, _, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("uuid-admin", "uuid-admin@example.com", role="admin")
        headers = build_headers(login_token(admin))
    response = client.delete("/api/storage/videos/not-a-uuid", headers=headers)
    assert response.status_code == 400

