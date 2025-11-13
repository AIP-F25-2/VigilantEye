import os
import threading
from collections import deque
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.app import create_app, db
from src.models.video import Video
from src.services.video_processor import (
    StreamError,
    VideoProcessingError,
    VideoProcessorService,
)
from pydub.exceptions import CouldntDecodeError


class DummyConfig:
    FRAME_EXTRACTION_INTERVAL = 1.0
    MOTION_DETECTION_THRESHOLD = 0.3
    MAX_CONCURRENT_STREAMS = 2
    STORAGE_BASE_PATH = ""
    THUMBNAIL_WIDTH = 320
    THUMBNAIL_HEIGHT = 240
    MAX_RESOLUTION_WIDTH = 3840
    MAX_RESOLUTION_HEIGHT = 2160
    MAX_VIDEO_SIZE_MB = 500
    FRAME_BUFFER_SIZE = 5
    FFMPEG_PATH = "ffmpeg"


@pytest.fixture(scope="module")
def app(tmp_path_factory, monkeypatch):
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    storage_base = tmp_path_factory.mktemp("video-processor")
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "user")
    monkeypatch.setenv("MYSQL_PASSWORD", "password")
    monkeypatch.setenv("MYSQL_DATABASE", "test_db")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret")
    DummyConfig.STORAGE_BASE_PATH = str(storage_base)
    test_app = create_app("development")
    test_app.config["TESTING"] = True
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def service(monkeypatch, tmp_path):
    DummyConfig.STORAGE_BASE_PATH = str(tmp_path)
    monkeypatch.setattr(VideoProcessorService, "_verify_ffmpeg", lambda self: True)
    return VideoProcessorService(DummyConfig())


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


def _mock_capture(mocker, *, opened=True, fps=30.0, frame_count=60, frames=None):
    capture = MagicMock()
    capture.isOpened.return_value = opened

    props: Dict[int, float] = {
        5: fps,  # cv2.CAP_PROP_FPS
        7: frame_count,  # cv2.CAP_PROP_FRAME_COUNT
        3: 1920,  # cv2.CAP_PROP_FRAME_WIDTH
        4: 1080,  # cv2.CAP_PROP_FRAME_HEIGHT
    }
    capture.get.side_effect = lambda prop: props.get(prop, 0.0)

    frames_iter = iter(frames or [])

    def _read():
        try:
            frame = next(frames_iter)
            return True, frame
        except StopIteration:
            return False, None

    capture.read.side_effect = _read
    mocker.patch("src.services.video_processor.cv2.VideoCapture", return_value=capture)
    return capture


def test_extract_metadata_success(service, mocker, tmp_path):
    _mock_capture(mocker)
    metadata, error = service.extract_metadata("dummy.mp4")
    assert error is None
    assert metadata == {
        "duration": pytest.approx(2.0),
        "fps": 30.0,
        "resolution": "1920x1080",
        "width": 1920,
        "height": 1080,
        "frame_count": 60,
    }


def test_extract_metadata_invalid_video(service, mocker):
    _mock_capture(mocker, opened=False)
    metadata, error = service.extract_metadata("missing.mp4")
    assert metadata is None
    assert isinstance(error, VideoProcessingError)


def test_generate_thumbnail_success(service, mocker, tmp_path):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cap = _mock_capture(mocker, frames=[frame])
    resize_mock = mocker.patch("src.services.video_processor.cv2.resize", return_value=frame)
    imwrite_mock = mocker.patch("src.services.video_processor.cv2.imwrite", return_value=True)
    output_path = str(tmp_path / "thumb.jpg")

    success, error = service.generate_thumbnail("video.mp4", output_path)
    assert success is True
    assert error is None
    cap.read.assert_called()
    resize_mock.assert_called_once()
    imwrite_mock.assert_called_once_with(output_path, frame)


def test_generate_thumbnail_no_frames(service, mocker):
    cap = _mock_capture(mocker, frames=[])
    success, error = service.generate_thumbnail("video.mp4", "thumb.jpg")
    assert success is False
    assert isinstance(error, VideoProcessingError)
    cap.read.assert_called()


def test_extract_frames_with_interval(service, mocker, tmp_path):
    frames = [
        np.full((100, 100, 3), idx, dtype=np.uint8) for idx in range(10)
    ]
    _mock_capture(mocker, fps=5.0, frames=frames)
    mocker.patch("src.services.video_processor.cv2.cvtColor", side_effect=lambda x, *_: x)
    mocker.patch("src.services.video_processor.cv2.GaussianBlur", side_effect=lambda x, *_: x)
    mocker.patch("src.services.video_processor.cv2.threshold", return_value=(None, np.ones((100, 100))))
    mocker.patch("src.services.video_processor.cv2.absdiff", return_value=np.zeros((100, 100)))
    imwrite_mock = mocker.patch("src.services.video_processor.cv2.imwrite", return_value=True)

    output_dir = tmp_path / "frames"
    extracted, error = service.extract_frames("video.mp4", str(output_dir), interval=1.0, use_motion_detection=False)
    assert error is None
    assert len(extracted) == 5  # fps * interval = 5 -> every frame since interval=1 sec and fps=5
    assert all(path.endswith(".jpg") for path in extracted)
    assert imwrite_mock.call_count == 5


def test_extract_frames_with_motion_detection(service, mocker, tmp_path):
    base_frame = np.zeros((100, 100), dtype=np.uint8)
    moving_frame = np.ones((100, 100), dtype=np.uint8) * 255

    frames = [
        np.stack([base_frame] * 3, axis=-1),
        np.stack([base_frame] * 3, axis=-1),
        np.stack([moving_frame] * 3, axis=-1),
    ]
    _mock_capture(mocker, fps=1.0, frames=frames)

    mocker.patch("src.services.video_processor.cv2.cvtColor", side_effect=lambda x, *_: x[:, :, 0])
    mocker.patch("src.services.video_processor.cv2.GaussianBlur", side_effect=lambda x, *_: x)
    mocker.patch("src.services.video_processor.cv2.absdiff", side_effect=lambda a, b: np.abs(a - b))
    mocker.patch(
        "src.services.video_processor.cv2.threshold",
        side_effect=lambda delta, *_: (None, np.where(delta > 0, 255, 0)),
    )
    imwrite_mock = mocker.patch("src.services.video_processor.cv2.imwrite", return_value=True)

    output_dir = tmp_path / "motion"
    extracted, error = service.extract_frames("video.mp4", str(output_dir), interval=1.0, use_motion_detection=True)
    assert error is None
    assert len(extracted) == 2  # second frame skipped due to no motion
    assert imwrite_mock.call_count == 2


def test_extract_audio_success(service, mocker, tmp_path):
    audio_mock = MagicMock()
    mocker.patch("src.services.video_processor.AudioSegment.from_file", return_value=audio_mock)
    output_path = str(tmp_path / "audio.wav")
    success, error = service.extract_audio("video.mp4", output_path)
    assert success is True
    assert error is None
    audio_mock.export.assert_called_once_with(output_path, format="wav")


def test_extract_audio_no_audio_track(service, mocker, tmp_path):
    mocker.patch(
        "src.services.video_processor.AudioSegment.from_file",
        side_effect=CouldntDecodeError("file contains no audio"),
    )
    success, error = service.extract_audio("video.mp4", str(tmp_path / "audio.wav"))
    assert success is False
    assert error is None


def test_extract_audio_ffmpeg_not_installed(service, mocker, tmp_path):
    service.ffmpeg_available = False
    success, error = service.extract_audio("video.mp4", str(tmp_path / "audio.wav"))
    assert success is False
    assert isinstance(error, VideoProcessingError)


def test_validate_video_success(service, mocker, tmp_path):
    video_path = tmp_path / "valid.mp4"
    video_path.write_bytes(b"x")
    _mock_capture(mocker, frames=[np.zeros((480, 640, 3), dtype=np.uint8)])

    is_valid, message = service.validate_video(str(video_path))
    assert is_valid is True
    assert message is None


def test_validate_video_exceeds_size_limit(service, mocker, tmp_path):
    video_path = tmp_path / "large.mp4"
    video_path.write_bytes(b"x")
    mocker.patch("src.services.video_processor.os.path.getsize", return_value=service.max_video_size_mb * 1024 * 1024 + 1)
    is_valid, message = service.validate_video(str(video_path))
    assert not is_valid
    assert "size" in message.lower()


def test_validate_video_exceeds_resolution_limit(service, mocker, tmp_path):
    video_path = tmp_path / "big.mp4"
    video_path.write_bytes(b"x")
    large_frame = np.zeros((service.max_resolution_height + 1, service.max_resolution_width + 1, 3), dtype=np.uint8)
    _mock_capture(mocker, frames=[large_frame])
    is_valid, message = service.validate_video(str(video_path))
    assert not is_valid
    assert "resolution" in message.lower()


def test_process_uploaded_video_success(service, mocker, app, tmp_path):
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"data")
    metadata = {
        "duration": 10.0,
        "fps": 25.0,
        "resolution": "1920x1080",
    }
    mocker.patch.object(service, "extract_metadata", return_value=(metadata, None))
    mocker.patch.object(
        service,
        "generate_thumbnail",
        return_value=(True, None),
    )
    mocker.patch.object(service, "_build_thumbnail_path", return_value=str(tmp_path / "clip-thumb.jpg"))

    with app.app_context():
        video = Video(
            filename="clip.mp4",
            filepath="relative/clip.mp4",
            upload_type="upload",
            user_id="user",
            status="uploading",
        )
        db.session.add(video)
        db.session.commit()

        mocker.patch.object(video, "get_storage_path", return_value=str(video_file))

        processed, error = service.process_uploaded_video(video)
        assert error is None
        assert processed is not None
        assert processed.duration == metadata["duration"]
        assert processed.status == "ready"


def test_process_uploaded_video_metadata_extraction_fails(service, mocker, app, tmp_path):
    video_file = tmp_path / "clip.mp4"
    video_file.write_bytes(b"data")
    mocker.patch.object(
        service,
        "extract_metadata",
        return_value=(None, VideoProcessingError("failed")),
    )

    with app.app_context():
        video = Video(
            filename="clip.mp4",
            filepath="relative/clip.mp4",
            upload_type="upload",
            user_id="user",
            status="uploading",
        )
        db.session.add(video)
        db.session.commit()

        mocker.patch.object(video, "get_storage_path", return_value=str(video_file))

        processed, error = service.process_uploaded_video(video)
        assert processed is None
        assert error is not None


def test_start_stream_success(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    started, error = service.start_stream("camera-1", "rtsp://example.com/stream")
    assert started is True
    assert error is None
    assert "camera-1" in service.active_streams
    service.stop_stream("camera-1")


def test_start_stream_max_concurrent_reached(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.max_concurrent_streams = 1
    service.start_stream("camera-1", "url")
    started, error = service.start_stream("camera-2", "url")
    assert not started
    assert isinstance(error, StreamError)
    service.stop_stream("camera-1")


def test_start_stream_already_active(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.start_stream("camera-1", "url")
    started, error = service.start_stream("camera-1", "url")
    assert not started
    assert isinstance(error, StreamError)
    service.stop_stream("camera-1")


def test_stop_stream_success(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.start_stream("camera-1", "url")
    stopped, error = service.stop_stream("camera-1")
    assert stopped
    assert error is None
    assert "camera-1" not in service.active_streams


def test_stop_stream_not_found(service):
    stopped, error = service.stop_stream("unknown")
    assert not stopped
    assert isinstance(error, StreamError)


def test_get_stream_frame_success(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.start_stream("camera-1", "url")
    with service.streams_lock:
        buffer = service.active_streams["camera-1"]["frame_buffer"]
        buffer.append(np.zeros((10, 10, 3), dtype=np.uint8))
    frame, error = service.get_stream_frame("camera-1")
    assert error is None
    assert frame is not None
    service.stop_stream("camera-1")


def test_get_stream_frame_no_frames_yet(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.start_stream("camera-1", "url")
    frame, error = service.get_stream_frame("camera-1")
    assert error is None
    assert frame is None
    service.stop_stream("camera-1")


def test_stream_worker_reconnection(service, mocker):
    frames = deque(
        [
            (False, None),  # initial failure
            (True, np.zeros((10, 10, 3), dtype=np.uint8)),
            (False, None),
        ]
    )

    class StreamCapture:
        def __init__(self):
            self.open_attempts = 0

        def isOpened(self):
            self.open_attempts += 1
            return self.open_attempts > 1

        def get(self, prop):
            if prop == 5:
                return 10.0
            return 0

        def read(self):
            return frames.popleft() if frames else (False, None)

        def release(self):
            return None

    capture = StreamCapture()
    mocker.patch("src.services.video_processor.cv2.VideoCapture", return_value=capture)
    stop_event = threading.Event()
    buffer: deque = deque(maxlen=service.frame_buffer_size)
    service._stream_worker("camera-1", "url", stop_event, buffer, None)
    assert capture.open_attempts > 1



def test_frame_buffer_overflow(service, mocker):
    mocker.patch.object(service, "_stream_worker", lambda *args, **kwargs: None)
    service.frame_buffer_size = 3
    service.start_stream("camera-1", "url")
    with service.streams_lock:
        buffer: deque = service.active_streams["camera-1"]["frame_buffer"]
        for idx in range(10):
            buffer.append(np.full((5, 5, 3), idx, dtype=np.uint8))
        assert len(buffer) == 3
        assert np.array_equal(buffer[0], np.full((5, 5, 3), 7, dtype=np.uint8))
    service.stop_stream("camera-1")


