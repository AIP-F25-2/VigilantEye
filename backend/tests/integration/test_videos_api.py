import io
import os
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import FileStorage

from src.app import create_app, db
from src.models.camera import Camera
from src.models.user import User
from src.models.video import Video
from src.services.storage_service import QuotaExceededError, StorageService
from src.services.video_processor import StreamError


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
        data = self.store.get(key, {})
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
        return {}

    def get(self, key: str) -> Any:
        return self.store.get(key)

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

    def clear(self) -> None:
        self.store.clear()


class FakeVideoProcessor:
    def __init__(self) -> None:
        self.streams_lock = threading.Lock()
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.validations: Dict[str, Tuple[bool, str | None]] = {}
        self.processed_videos: list[str] = []
        self.max_concurrent_streams = 4

    def validate_video(self, video_path: str) -> Tuple[bool, str | None]:
        return self.validations.get(video_path, (True, None))

    def process_uploaded_video(self, video: Video) -> Tuple[Video | None, Exception | None]:
        self.processed_videos.append(video.id)
        video.duration = 12.5
        video.fps = 30
        video.resolution = "1920x1080"
        video.mark_ready()
        db.session.commit()
        return video, None

    def start_stream(self, camera_id: str, stream_url: str, frame_callback=None):
        with self.streams_lock:
            if camera_id in self.active_streams:
                return False, StreamError("Stream already active for this camera")
            if len(self.active_streams) >= self.max_concurrent_streams:
                return False, StreamError("Maximum concurrent streams reached")
            self.active_streams[camera_id] = {
                "stream_url": stream_url,
                "frame_buffer": deque(maxlen=100),
                "started_at": datetime.utcnow(),
            }
        return True, None

    def stop_stream(self, camera_id: str):
        with self.streams_lock:
            if camera_id not in self.active_streams:
                return False, StreamError("Stream not found")
            del self.active_streams[camera_id]
        return True, None

    def get_stream_frame(self, camera_id: str):
        with self.streams_lock:
            if camera_id not in self.active_streams:
                return None, StreamError("Stream not found")
            buffer = self.active_streams[camera_id]["frame_buffer"]
            return (buffer[-1] if buffer else None), None


def _reset_storage(monkeypatch, storage_dir: Path) -> StorageService:
    StorageService._instance = None
    StorageService._initialized = False
    monkeypatch.setenv("STORAGE_BASE_PATH", str(storage_dir))
    monkeypatch.setenv("SUPPORTED_VIDEO_FORMATS", "mp4,avi")
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "500")
    return StorageService()


@pytest.fixture(scope="session")
def app_fixture(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("JWT_SECRET_KEY", "jwt-secret")
    os.environ.setdefault("MYSQL_HOST", "localhost")
    os.environ.setdefault("MYSQL_USER", "root")
    os.environ.setdefault("MYSQL_PASSWORD", "password")
    os.environ.setdefault("MYSQL_DATABASE", "vigilanteye")
    os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/5")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/6")

    storage_dir = tmp_path_factory.mktemp("videos-api-storage")
    fake_redis = FakeRedis()
    monkeypatch.setenv("FRAME_EXTRACTION_INTERVAL", "1.0")
    monkeypatch.setenv("MAX_CONCURRENT_STREAMS", "4")
    monkeypatch.setenv("MOTION_DETECTION_THRESHOLD", "0.3")
    storage_service = _reset_storage(monkeypatch, storage_dir)
    fake_processor = FakeVideoProcessor()

    monkeypatch.setattr(
        "src.services.storage_service.redis.from_url", lambda *_args, **_kwargs: fake_redis
    )
    monkeypatch.setattr(
        "src.services.auth_service.redis.from_url", lambda *_args, **_kwargs: fake_redis
    )

    from src.api import videos as videos_module

    videos_module.storage_service = storage_service
    videos_module.video_processor = fake_processor
    videos_module.video_processor.max_concurrent_streams = 4

    test_app = create_app("development")
    test_app.config["TESTING"] = True
    test_app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    with test_app.app_context():
        db.create_all()
        yield test_app, storage_service, fake_processor, storage_dir, fake_redis, videos_module
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_fixture):
    app, *_ = app_fixture
    with app.test_client() as testing_client:
        yield testing_client


@pytest.fixture(autouse=True)
def clean_state(app_fixture):
    app, storage_service, fake_processor, storage_dir, fake_redis, _ = app_fixture
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    fake_processor.active_streams.clear()
    fake_processor.validations.clear()
    fake_processor.processed_videos.clear()
    fake_redis.clear()
    for path in Path(storage_dir).rglob("*"):
        if path.is_file():
            path.unlink()
    yield
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    fake_processor.active_streams.clear()
    fake_redis.clear()


def create_user(username: str, email: str, role: str = "staff") -> User:
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password("Password123")
    db.session.add(user)
    db.session.commit()
    return user


def auth_headers(app, user: User) -> Dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=user)
    return {"Authorization": f"Bearer {token}"}


def make_video_file(filename: str = "clip.mp4") -> FileStorage:
    return FileStorage(stream=io.BytesIO(b"video-bytes"), filename=filename, content_length=len(b"video-bytes"))


def upload_video_record(storage_service: StorageService, user: User, filename: str = "clip.mp4") -> Video:
    file_storage = make_video_file(filename)
    video, error = storage_service.save_video(file_storage, user.id)
    assert error is None
    return video


def test_upload_video_success(app_fixture, client):
    app, storage_service, fake_processor, storage_dir, _, _ = app_fixture
    with app.app_context():
        user = create_user("staff", "staff@example.com")
        existing_count = Video.query.count()

    data = {"video": (io.BytesIO(b"video-bytes"), "clip.mp4")}
    response = client.post(
        "/api/videos/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers(app, user),
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["message"] == "Video uploaded successfully"
    with app.app_context():
        assert Video.query.count() == existing_count + 1
        video = Video.query.first()
        assert video.duration == 12.5
        assert video.status == "ready"
        thumb_path = Path(storage_dir) / Path(video.filepath).with_suffix("-thumb.jpg")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)


def test_upload_video_without_auth(client):
    response = client.post(
        "/api/videos/upload",
        data={"video": (io.BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 401


def test_upload_video_invalid_format(app_fixture, client):
    app, _, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("staff-invalid", "staff-invalid@example.com")
    response = client.post(
        "/api/videos/upload",
        data={"video": (io.BytesIO(b"video"), "clip.txt")},
        content_type="multipart/form-data",
        headers=auth_headers(app, user),
    )
    assert response.status_code == 400


def test_upload_video_exceeds_size_limit(app_fixture, client, monkeypatch):
    app, storage_service, _, _, _, videos_module = app_fixture
    with app.app_context():
        user = create_user("staff-large", "staff-large@example.com")

    def _save_video(*_args, **_kwargs):
        return None, QuotaExceededError("Video exceeds maximum allowed size")

    monkeypatch.setattr(videos_module.storage_service, "save_video", _save_video)
    response = client.post(
        "/api/videos/upload",
        data={"video": (io.BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
        headers=auth_headers(app, user),
    )
    assert response.status_code == 413


def test_upload_video_quota_exceeded(app_fixture, client, monkeypatch):
    app, storage_service, _, _, _, videos_module = app_fixture
    with app.app_context():
        user = create_user("staff-quota", "staff-quota@example.com")

    def _save_video(*_args, **_kwargs):
        return None, QuotaExceededError("User storage quota exceeded")

    monkeypatch.setattr(videos_module.storage_service, "save_video", _save_video)
    response = client.post(
        "/api/videos/upload",
        data={"video": (io.BytesIO(b"video"), "clip.mp4")},
        content_type="multipart/form-data",
        headers=auth_headers(app, user),
    )
    assert response.status_code == 409


def test_start_stream_success(app_fixture, client):
    app, _, fake_processor, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("stream-user", "stream@example.com")
    payload = {"camera_id": "11111111-1111-1111-1111-111111111111", "stream_url": "rtsp://camera/1"}
    response = client.post("/api/videos/start-stream", json=payload, headers=auth_headers(app, user))
    assert response.status_code == 201
    with app.app_context():
        camera = Camera.query.filter_by(id=payload["camera_id"]).first()
        assert camera is not None
        assert camera.status == "active"
        video = Video.query.filter_by(camera_id=camera.id, upload_type="stream").first()
        assert video is not None
    assert payload["camera_id"] in fake_processor.active_streams


def test_start_stream_max_concurrent_reached(app_fixture, client):
    app, _, fake_processor, _, _, _ = app_fixture
    fake_processor.max_concurrent_streams = 1
    with app.app_context():
        user = create_user("stream-limit", "stream-limit@example.com")
    first_payload = {"camera_id": "11111111-1111-1111-1111-111111111110", "stream_url": "rtsp://camera/primary"}
    second_payload = {"camera_id": "11111111-1111-1111-1111-111111111111", "stream_url": "rtsp://camera/secondary"}
    client.post("/api/videos/start-stream", json=first_payload, headers=auth_headers(app, user))
    response = client.post("/api/videos/start-stream", json=second_payload, headers=auth_headers(app, user))
    assert response.status_code == 429


def test_start_stream_already_active(app_fixture, client):
    app, _, fake_processor, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("stream-dup", "stream-dup@example.com")
    payload = {"camera_id": "11111111-1111-1111-1111-111111111112", "stream_url": "rtsp://camera/dup"}
    client.post("/api/videos/start-stream", json=payload, headers=auth_headers(app, user))
    response = client.post("/api/videos/start-stream", json=payload, headers=auth_headers(app, user))
    assert response.status_code == 409


def test_stop_stream_success(app_fixture, client):
    app, _, fake_processor, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("stream-stop", "stream-stop@example.com")
    payload = {"camera_id": "11111111-1111-1111-1111-111111111113", "stream_url": "rtsp://camera/stop"}
    client.post("/api/videos/start-stream", json=payload, headers=auth_headers(app, user))
    response = client.post(
        "/api/videos/stop-stream",
        json={"camera_id": payload["camera_id"]},
        headers=auth_headers(app, user),
    )
    assert response.status_code == 200
    assert payload["camera_id"] not in fake_processor.active_streams


def test_stop_stream_not_found(app_fixture, client):
    app, _, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("stream-none", "stream-none@example.com")
    response = client.post(
        "/api/videos/stop-stream",
        json={"camera_id": "11111111-1111-1111-1111-111111111199"},
        headers=auth_headers(app, user),
    )
    assert response.status_code == 404


def test_list_videos_own(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("list-own", "list-own@example.com")
        other_user = create_user("list-other", "list-other@example.com")
        upload_video_record(storage_service, user)
        upload_video_record(storage_service, other_user)
    response = client.get("/api/videos/", headers=auth_headers(app, user))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["filename"].endswith("clip.mp4")


def test_list_videos_admin_sees_all(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        admin = create_user("admin-list", "admin-list@example.com", role="admin")
        user_a = create_user("user-a", "user-a@example.com")
        user_b = create_user("user-b", "user-b@example.com")
        upload_video_record(storage_service, user_a)
        upload_video_record(storage_service, user_b)
    response = client.get("/api/videos/", headers=auth_headers(app, admin))
    assert response.status_code == 200
    data = response.get_json()
    assert data["pagination"]["total"] == 2


def test_list_videos_with_filters(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("filter-user", "filter-user@example.com")
        ready_video = upload_video_record(storage_service, user)
        ready_video.mark_ready()
        ready_video.camera_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        db.session.commit()

        processing_video = upload_video_record(storage_service, user, filename="processing.mp4")
        processing_video.status = "processing"
        processing_video.camera_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        db.session.commit()

    url = "/api/videos/?status=ready&camera_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    response = client.get(url, headers=auth_headers(app, user))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["videos"]) == 1
    assert data["videos"][0]["status"] == "ready"


def test_list_videos_pagination(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("pager", "pager@example.com")
        for idx in range(30):
            upload_video_record(storage_service, user, filename=f"video-{idx}.mp4")
    response_page1 = client.get("/api/videos/?page=1&per_page=10", headers=auth_headers(app, user))
    response_page2 = client.get("/api/videos/?page=2&per_page=10", headers=auth_headers(app, user))
    assert response_page1.status_code == 200
    assert response_page2.status_code == 200
    assert len(response_page1.get_json()["videos"]) == 10
    assert len(response_page2.get_json()["videos"]) == 10


def test_get_video_details_own(app_fixture, client):
    app, storage_service, _, storage_dir, _, _ = app_fixture
    with app.app_context():
        user = create_user("details", "details@example.com")
        video = upload_video_record(storage_service, user)
    response = client.get(f"/api/videos/{video.id}", headers=auth_headers(app, user))
    assert response.status_code == 200
    data = response.get_json()["video"]
    assert data["id"] == video.id


def test_get_video_details_other_as_staff(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        owner = create_user("owner", "owner@example.com")
        other = create_user("other", "other@example.com")
        video = upload_video_record(storage_service, owner)
    response = client.get(f"/api/videos/{video.id}", headers=auth_headers(app, other))
    assert response.status_code == 403


def test_get_video_details_other_as_admin(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        owner = create_user("owner-admin", "owner-admin@example.com")
        admin = create_user("admin", "admin@example.com", role="admin")
        video = upload_video_record(storage_service, owner)
    response = client.get(f"/api/videos/{video.id}", headers=auth_headers(app, admin))
    assert response.status_code == 200


def test_get_thumbnail_success(app_fixture, client):
    app, storage_service, _, storage_dir, _, _ = app_fixture
    with app.app_context():
        user = create_user("thumb-user", "thumb@example.com")
        video = upload_video_record(storage_service, user)
        thumb_path = Path(storage_dir) / Path(video.filepath).with_suffix("-thumb.jpg")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"thumbnail")
    response = client.get(f"/api/videos/{video.id}/thumbnail", headers=auth_headers(app, user))
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/jpeg"


def test_get_thumbnail_not_found(app_fixture, client):
    app, storage_service, _, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("thumb-missing", "thumb-missing@example.com")
        video = upload_video_record(storage_service, user)
    response = client.get(f"/api/videos/{video.id}/thumbnail", headers=auth_headers(app, user))
    assert response.status_code == 404


def test_get_active_streams(app_fixture, client):
    app, _, fake_processor, _, _, _ = app_fixture
    with app.app_context():
        user = create_user("active-stream", "active-stream@example.com")
    payload_a = {"camera_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001", "stream_url": "rtsp://camera/a"}
    payload_b = {"camera_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002", "stream_url": "rtsp://camera/b"}
    client.post("/api/videos/start-stream", json=payload_a, headers=auth_headers(app, user))
    client.post("/api/videos/start-stream", json=payload_b, headers=auth_headers(app, user))
    response = client.get("/api/videos/streams/active", headers=auth_headers(app, user))
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2
    assert len(data["active_streams"]) == 2


def test_cors_headers(client):
    response = client.options("/api/videos/upload", headers={"Origin": "http://localhost"})
    assert response.status_code in {200, 204}
    assert "Access-Control-Allow-Origin" in response.headers


