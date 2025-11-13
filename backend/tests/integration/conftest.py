"""Integration test specific fixtures for API testing."""

import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import MagicMock
from werkzeug.datastructures import FileStorage

import pytest

from src.models.video import Video
from src.services.video_processor import StreamError


class FakeVideoProcessor:
    """Fake video processor for integration tests."""

    def __init__(self):
        self.streams_lock = threading.Lock()
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.validations: Dict[str, Tuple[bool, str | None]] = {}
        self.processed_videos: list[str] = []
        self.max_concurrent_streams = 4

    def validate_video(self, video_path: str) -> Tuple[bool, str | None]:
        """Validate video file."""
        return self.validations.get(video_path, (True, None))

    def process_uploaded_video(self, video: Video) -> Tuple[Video | None, Exception | None]:
        """Process uploaded video."""
        self.processed_videos.append(video.id)
        video.duration = 12.5
        video.fps = 30
        video.resolution = "1920x1080"
        video.mark_ready()
        from src.app import db

        db.session.commit()
        return video, None

    def start_stream(self, camera_id: str, stream_url: str, frame_callback=None):
        """Start video stream."""
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
        """Stop video stream."""
        with self.streams_lock:
            if camera_id not in self.active_streams:
                return False, StreamError("Stream not found")
            del self.active_streams[camera_id]
        return True, None

    def get_stream_frame(self, camera_id: str):
        """Get stream frame."""
        with self.streams_lock:
            if camera_id not in self.active_streams:
                return None, StreamError("Stream not found")
            buffer = self.active_streams[camera_id]["frame_buffer"]
            return (buffer[-1] if buffer else None), None


@pytest.fixture(scope="session")
def test_storage_dir(tmp_path_factory):
    """Create temporary storage directory for integration tests."""
    storage_dir = tmp_path_factory.mktemp("test_storage")
    (storage_dir / "videos").mkdir()
    (storage_dir / "frames").mkdir()
    (storage_dir / "audio").mkdir()
    (storage_dir / "evidence").mkdir()
    (storage_dir / "persons").mkdir()
    (storage_dir / "reports").mkdir()
    return storage_dir


@pytest.fixture
def mock_video_processor(monkeypatch):
    """Mock video processor service."""
    fake_processor = FakeVideoProcessor()
    monkeypatch.setattr("src.services.video_processor.VideoProcessorService", lambda *_, **__: fake_processor)
    monkeypatch.setattr("src.api.videos.video_processor_service", fake_processor)
    return fake_processor


@pytest.fixture
def mock_telegram_bot(monkeypatch):
    """Mock Telegram bot to avoid actual API calls."""
    import sys
    
    mock_bot = MagicMock()
    mock_bot.send_message = MagicMock(return_value=MagicMock(message_id=123))
    mock_bot.send_photo = MagicMock(return_value=MagicMock(message_id=124))
    mock_bot.send_audio = MagicMock(return_value=MagicMock(message_id=125))
    mock_bot.answer_callback_query = MagicMock(return_value=True)
    mock_bot.edit_message_reply_markup = MagicMock(return_value=True)
    mock_bot.set_webhook = MagicMock(return_value=True)
    mock_bot.delete_webhook = MagicMock(return_value=True)
    mock_bot.get_webhook_info = MagicMock(return_value={"url": "https://example.com/webhook"})

    # Mock telegram module without importing it
    mock_telegram = MagicMock()
    mock_telegram.Bot = MagicMock(return_value=mock_bot)
    mock_module = MagicMock()
    mock_module.Bot = mock_telegram.Bot
    monkeypatch.setitem(sys.modules, "telegram", mock_module)

    return mock_bot


@pytest.fixture
def mock_ollama_client(monkeypatch):
    """Mock Ollama client to avoid actual service calls."""
    mock_client = MagicMock()
    mock_client.list.return_value = {"models": [{"name": "llama3.2:1b"}]}
    mock_client.pull.return_value = {"status": "success"}
    mock_client.generate.return_value = {
        "response": '{"is_suspicious": true, "confidence": 0.92, "threat_level": "high", "reasoning": "Test reasoning", "recommended_action": "alert", "key_factors": ["weapon", "night"]}'
    }

    # Mock ollama.Client
    mock_ollama = MagicMock()
    mock_ollama.Client = MagicMock(return_value=mock_client)
    monkeypatch.setitem(__import__("ollama", fromlist=["Client"]).__dict__, "Client", mock_ollama.Client)

    return mock_client


@pytest.fixture
def sample_ai_outputs():
    """Return complete AI outputs dict from all 5 modules."""
    return {
        "scene": {
            "scene_type": "outdoor",
            "lighting": "dark",
            "weather": "clear",
            "crowd_density": "sparse",
            "description": "Outdoor parking lot at night",
            "confidence": 0.85,
        },
        "persons": [
            {
                "person_id": "person_123",
                "age": 25,
                "gender": "male",
                "bbox": [100, 100, 200, 300],
                "confidence": 0.89,
                "clothing_description": "Dark jacket, black pants",
            }
        ],
        "objects": {
            "objects": [
                {
                    "class_name": "knife",
                    "threat_level": "high",
                    "confidence": 0.92,
                    "bbox": [150, 150, 180, 200],
                }
            ],
            "relationships": [
                {
                    "person_id": "person_123",
                    "object_id": "obj_1",
                    "relationship": "holding",
                    "object_threat_level": "high",
                }
            ],
            "threat_summary": {"max_threat_level": "high", "high_threat_count": 1},
        },
        "transcription": {
            "text": "",
            "language": "unknown",
            "threat_keywords": [],
            "profanity_detected": False,
            "confidence": 0.0,
        },
        "audio_events": {
            "detected_sounds": [
                {
                    "class_name": "Glass",
                    "urgency_level": "high",
                    "timestamp": 42.5,
                    "confidence": 0.91,
                }
            ],
            "urgency_summary": {"max_urgency": "high", "high_count": 1},
            "confidence": 0.91,
        },
    }


# Helper functions
def create_test_video_file(filename: str = "test.mp4", size_bytes: int = 1024) -> FileStorage:
    """Create in-memory video file for upload tests."""
    from io import BytesIO

    data = b"fake video data" * (size_bytes // 16 + 1)
    return FileStorage(
        stream=BytesIO(data[:size_bytes]), filename=filename, content_type="video/mp4"
    )


def upload_video_via_api(client, user, filename: str = "test.mp4"):
    """Upload video via API and return Video object."""
    from src.app import db
    from flask_jwt_extended import create_access_token

    token = create_access_token(identity=str(user.id))
    video_file = create_test_video_file(filename)
    response = client.post(
        "/api/videos/upload",
        data={"file": video_file},
        headers={"Authorization": f"Bearer {token}"},
        content_type="multipart/form-data",
    )
    if response.status_code == 201:
        video_id = response.json["video"]["id"]
        return db.session.get(Video, video_id)
    return None


def create_ticket_via_api(client, user, video_id: str):
    """Create ticket via API."""
    from flask_jwt_extended import create_access_token

    token = create_access_token(identity=str(user.id))
    response = client.post(
        "/api/tickets",
        json={
            "video_id": video_id,
            "title": "Test Ticket",
            "description": "Test description",
            "priority": "medium",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code == 201:
        return response.json["ticket"]
    return None
