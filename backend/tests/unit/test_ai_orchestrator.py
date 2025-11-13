import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.app import create_app, db
from src.config.constants import AnalysisResult, UserRole, VideoStatus
from src.models.ai_performance_metrics import AIPerformanceMetrics
from src.models.user import User
from src.models.video import Video
from src.services.ai_orchestrator import AIOrchestrator, AnalysisError


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
def staff_user(app):
    with app.app_context():
        user = User(username="staff1", email="staff1@test.com", role=UserRole.STAFF, is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_video(app, staff_user):
    with app.app_context():
        video = Video(
            filename="test.mp4",
            filepath="videos/test.mp4",
            user_id=str(staff_user.id),
            upload_type="upload",
            status=VideoStatus.READY.value,
        )
        db.session.add(video)
        db.session.commit()
        return video


@pytest.fixture
def mock_ai_services():
    """Mock all AI services."""
    with patch("src.services.ai_orchestrator.PersonDetectorService") as person_mock, patch(
        "src.services.ai_orchestrator.SceneAnalyzerService"
    ) as scene_mock, patch("src.services.ai_orchestrator.ObjectDetectorService") as object_mock, patch(
        "src.services.ai_orchestrator.SpeechToTextService"
    ) as speech_mock, patch("src.services.ai_orchestrator.AudioClassifierService") as audio_mock, patch(
        "src.services.ai_orchestrator.LLMAnalyzerService"
    ) as llm_mock:
        person_instance = Mock()
        person_instance.detect_persons.return_value = ([{"person_id": "p1"}], None)

        scene_instance = Mock()
        scene_instance.analyze_scene.return_value = ({"scene_type": "indoor", "lighting": "bright"}, None)

        object_instance = Mock()
        object_instance.detect_objects.return_value = ({"objects": [], "relationships": []}, None)

        speech_instance = Mock()
        speech_instance.transcribe_audio.return_value = ({"transcription": "test"}, None)

        audio_instance = Mock()
        audio_instance.classify_audio.return_value = ({"detected_sounds": []}, None)

        llm_instance = Mock()
        llm_instance.analyze_situation.return_value = (
            {"is_suspicious": True, "confidence": 0.92, "threat_level": "high"},
            None,
        )

        person_mock.return_value = person_instance
        scene_mock.return_value = scene_instance
        object_mock.return_value = object_instance
        speech_mock.return_value = speech_instance
        audio_mock.return_value = audio_instance
        llm_mock.return_value = llm_instance

        yield {
            "person": person_instance,
            "scene": scene_instance,
            "object": object_instance,
            "speech": speech_instance,
            "audio": audio_instance,
            "llm": llm_instance,
        }


@pytest.fixture
def mock_supporting_services():
    """Mock supporting services."""
    with patch("src.services.ai_orchestrator.VideoProcessorService") as video_mock, patch(
        "src.services.ai_orchestrator.StorageService"
    ) as storage_mock, patch("src.services.ai_orchestrator.TicketService") as ticket_mock, patch(
        "src.services.ai_orchestrator.MessengerService"
    ) as messenger_mock:
        video_instance = Mock()
        video_instance.extract_frames.return_value = (["frame1.jpg", "frame2.jpg"], None)
        video_instance.extract_audio.return_value = (True, None)

        storage_instance = Mock()
        storage_instance.save_frame.return_value = (Mock(filepath="evidence/frame.jpg"), None)
        storage_instance.save_audio.return_value = (Mock(filepath="evidence/audio.wav"), None)

        ticket_instance = Mock()
        ticket_instance.create_ticket.return_value = (Mock(id="ticket1"), None)

        messenger_instance = Mock()
        messenger_instance.send_alert.return_value = (True, None)

        video_mock.return_value = video_instance
        storage_mock.return_value = storage_instance
        ticket_mock.return_value = ticket_instance
        messenger_mock.return_value = messenger_instance

        yield {
            "video": video_instance,
            "storage": storage_instance,
            "ticket": ticket_instance,
            "messenger": messenger_instance,
        }


@pytest.fixture
def mock_websocket():
    """Mock WebSocket emission."""
    with patch("src.utils.websocket_utils.socketio") as socketio_mock:
        yield socketio_mock


def test_analyze_video_success_suspicious(app, test_video, mock_ai_services, mock_supporting_services, mock_websocket):
    """Test successful analysis with suspicious result."""
    with app.app_context():
        with patch("os.path.exists", return_value=True), patch("builtins.open", create=True), patch(
            "cv2.imread", return_value=Mock()
        ):
            orchestrator = AIOrchestrator()
            result, error = orchestrator.analyze_video(str(test_video.id))

            assert error is None
            assert result["is_suspicious"] is True
            assert result["confidence"] == 0.92

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZED.value
            assert video.analysis_result == AnalysisResult.SUSPICIOUS.value

            # Verify AI modules called
            mock_ai_services["person"].detect_persons.assert_called_once()
            mock_ai_services["scene"].analyze_scene.assert_called_once()
            mock_ai_services["object"].detect_objects.assert_called_once()
            mock_ai_services["llm"].analyze_situation.assert_called_once()

            # Verify ticket created
            mock_supporting_services["ticket"].create_ticket.assert_called_once()

            # Verify alert sent
            mock_supporting_services["messenger"].send_alert.assert_called_once()


def test_analyze_video_success_clean(app, test_video, mock_ai_services, mock_supporting_services, mock_websocket):
    """Test successful analysis with clean result."""
    with app.app_context():
        # Mock LLM to return clean result
        mock_ai_services["llm"].analyze_situation.return_value = (
            {"is_suspicious": False, "confidence": 0.88},
            None,
        )

        with patch("os.path.exists", return_value=True), patch("builtins.open", create=True), patch(
            "cv2.imread", return_value=Mock()
        ):
            orchestrator = AIOrchestrator()
            result, error = orchestrator.analyze_video(str(test_video.id))

            assert error is None
            assert result["is_suspicious"] is False

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZED.value
            assert video.analysis_result == AnalysisResult.CLEAN.value

            # Verify no ticket created
            mock_supporting_services["ticket"].create_ticket.assert_not_called()


def test_analyze_video_partial_ai_failure(app, test_video, mock_ai_services, mock_supporting_services, mock_websocket):
    """Test analysis with partial AI failures."""
    with app.app_context():
        # Mock some AI modules to fail
        mock_ai_services["scene"].analyze_scene.return_value = (None, Exception("BLIP-2 unavailable"))
        mock_ai_services["speech"].transcribe_audio.return_value = (None, Exception("No audio"))

        with patch("os.path.exists", return_value=True), patch("builtins.open", create=True), patch(
            "cv2.imread", return_value=Mock()
        ):
            orchestrator = AIOrchestrator()
            result, error = orchestrator.analyze_video(str(test_video.id))

            # Analysis should continue with partial results
            assert error is None
            # LLM should still be called with partial results
            mock_ai_services["llm"].analyze_situation.assert_called_once()


def test_analyze_video_video_not_found(app, mock_ai_services):
    """Test analysis with non-existent video."""
    with app.app_context():
        orchestrator = AIOrchestrator()
        result, error = orchestrator.analyze_video("nonexistent-id")

        assert result is None
        assert isinstance(error, AnalysisError)
        assert "not found" in str(error).lower()


def test_run_parallel_ai_analysis_all_succeed(app, mock_ai_services):
    """Test parallel AI analysis with all modules succeeding."""
    with app.app_context():
        frames = ["frame1.jpg", "frame2.jpg"]
        audio_path = "audio.wav"

        with patch("os.path.exists", return_value=True), patch("cv2.imread", return_value=Mock()):
            orchestrator = AIOrchestrator()
            ai_results = orchestrator._run_parallel_ai_analysis("video1", frames, audio_path)

            assert ai_results["persons"] is not None
            assert ai_results["scene"] is not None
            assert ai_results["objects"] is not None
            assert ai_results["transcription"] is not None
            assert ai_results["audio_events"] is not None
            assert len(ai_results["errors"]) == 0


def test_handle_analysis_result_suspicious(app, test_video, mock_supporting_services, mock_websocket):
    """Test handling suspicious analysis result."""
    with app.app_context():
        llm_result = {"is_suspicious": True, "confidence": 0.92, "threat_level": "high"}
        ai_results = {"persons": [{"person_id": "p1"}]}
        frames = ["frame1.jpg"]
        audio_path = "audio.wav"

        with patch("os.path.exists", return_value=True), patch("builtins.open", create=True), patch(
            "cv2.imread", return_value=Mock()
        ):
            orchestrator = AIOrchestrator()
            orchestrator._handle_analysis_result(str(test_video.id), llm_result, ai_results, frames, audio_path)

            # Verify ticket created
            mock_supporting_services["ticket"].create_ticket.assert_called_once()

            # Verify evidence stored
            mock_supporting_services["storage"].save_frame.assert_called_once()
            mock_supporting_services["storage"].save_audio.assert_called_once()

            # Verify alert sent
            mock_supporting_services["messenger"].send_alert.assert_called_once()


def test_handle_analysis_result_not_suspicious(app, test_video, mock_supporting_services, mock_websocket):
    """Test handling clean analysis result."""
    with app.app_context():
        llm_result = {"is_suspicious": False, "confidence": 0.88}
        ai_results = {}
        frames = []
        audio_path = None

        orchestrator = AIOrchestrator()
        orchestrator._handle_analysis_result(str(test_video.id), llm_result, ai_results, frames, audio_path)

        # Verify no ticket created
        mock_supporting_services["ticket"].create_ticket.assert_not_called()


def test_track_performance(app):
    """Test performance tracking."""
    with app.app_context():
        orchestrator = AIOrchestrator()
        orchestrator._track_performance("person_detection", "yolov8n", 150, "video1", "success")

        # Verify metric created
        metric = AIPerformanceMetrics.query.filter_by(task_name="person_detection").first()
        assert metric is not None
        assert metric.duration_ms == 150
        assert metric.status == "success"


def test_select_representative_frame(app):
    """Test representative frame selection."""
    with app.app_context():
        frames = ["frame1.jpg", "frame2.jpg", "frame3.jpg"]
        mock_frame = Mock()

        with patch("cv2.imread", return_value=mock_frame):
            orchestrator = AIOrchestrator()
            frame_path, frame_array, frame_number = orchestrator._select_representative_frame(frames)

            assert frame_path == "frame2.jpg"  # Middle frame
            assert frame_array == mock_frame
            assert frame_number == 1

