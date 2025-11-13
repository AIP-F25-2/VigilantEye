import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.app import create_app, db
from src.config.constants import AnalysisResult, UserRole, VideoStatus
from src.models.user import User
from src.models.video import Video
from src.tasks.analysis_tasks import (
    analyze_video_task,
    extract_frames_task,
    handle_suspicious_result_task,
    run_ai_models_task,
)


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
            filename="test_video.mp4",
            filepath="videos/test_video.mp4",
            user_id=str(staff_user.id),
            upload_type="upload",
            status=VideoStatus.READY.value,
        )
        db.session.add(video)
        db.session.commit()
        return video


@pytest.fixture
def mock_orchestrator():
    """Mock AIOrchestrator with all dependencies."""
    with patch("src.tasks.analysis_tasks.AIOrchestrator") as mock:
        orchestrator_instance = MagicMock()
        mock.return_value = orchestrator_instance

        # Mock video processor
        orchestrator_instance.video_processor.extract_frames.return_value = (
            ["frame1.jpg", "frame2.jpg", "frame3.jpg"],
            None,
        )
        orchestrator_instance.video_processor.extract_audio.return_value = (True, None)

        # Mock AI analysis
        orchestrator_instance._run_parallel_ai_analysis.return_value = {
            "scene": {"scene_type": "outdoor"},
            "persons": [{"person_id": "person1"}],
            "objects": {"objects": []},
            "transcription": {"transcription": "test"},
            "audio_events": {"detected_sounds": []},
            "errors": [],
        }

        # Mock LLM analyzer
        orchestrator_instance.llm_analyzer.analyze_situation.return_value = (
            {
                "is_suspicious": True,
                "confidence": 0.92,
                "threat_level": "high",
                "reasoning": "Test reasoning",
            },
            None,
        )
        orchestrator_instance._fallback_analysis.return_value = {
            "is_suspicious": False,
            "confidence": 0.6,
        }

        # Mock performance tracking
        orchestrator_instance._track_performance.return_value = None

        # Mock result handling
        orchestrator_instance._handle_analysis_result.return_value = None

        yield orchestrator_instance


@pytest.fixture
def mock_websocket():
    """Mock WebSocket emission."""
    with patch("src.tasks.analysis_tasks.emit_analysis_started") as mock_started, patch(
        "src.tasks.analysis_tasks.emit_frames_extracted"
    ) as mock_frames, patch("src.tasks.analysis_tasks.emit_ai_processing_started") as mock_ai, patch(
        "src.tasks.analysis_tasks.emit_llm_analysis_complete"
    ) as mock_llm, patch("src.tasks.analysis_tasks.emit_analysis_complete") as mock_complete, patch(
        "src.tasks.analysis_tasks.emit_analysis_error"
    ) as mock_error:
        yield {
            "started": mock_started,
            "frames": mock_frames,
            "ai": mock_ai,
            "llm": mock_llm,
            "complete": mock_complete,
            "error": mock_error,
        }


class TestAnalyzeVideoTask:
    """Test analyze_video_task entry point."""

    def test_analyze_video_task_success(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test successful analysis task start."""
        with app.app_context():
            result = analyze_video_task.apply(args=[test_video.id])

            assert result.successful()
            assert result.result["video_id"] == test_video.id
            assert result.result["status"] == "started"

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZING.value

            # Verify WebSocket event emitted
            mock_websocket["started"].assert_called_once_with(test_video.id)

    def test_analyze_video_task_video_not_found(self, app, mock_websocket):
        """Test task fails when video not found."""
        with app.app_context():
            with pytest.raises(ValueError, match="Video not found"):
                analyze_video_task.apply(args=["nonexistent-id"])

            mock_websocket["error"].assert_called_once()


class TestExtractFramesTask:
    """Test extract_frames_task."""

    def test_extract_frames_task_success(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test successful frame extraction."""
        with app.app_context():
            result = extract_frames_task.apply(args=[test_video.id])

            assert result.successful()
            assert result.result["video_id"] == test_video.id
            assert len(result.result["frames"]) == 3
            assert result.result["audio_path"] is not None

            # Verify WebSocket event emitted
            mock_websocket["frames"].assert_called_once_with(test_video.id, 3)

            # Verify performance tracking called
            assert mock_orchestrator._track_performance.call_count >= 2

    def test_extract_frames_task_no_audio(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test frame extraction continues when audio extraction fails."""
        with app.app_context():
            mock_orchestrator.video_processor.extract_audio.return_value = (False, Exception("No audio track"))

            result = extract_frames_task.apply(args=[test_video.id])

            assert result.successful()
            assert result.result["audio_path"] is None

    def test_extract_frames_task_video_not_found(self, app, mock_websocket):
        """Test task fails when video not found."""
        with app.app_context():
            with pytest.raises(ValueError, match="Video not found"):
                extract_frames_task.apply(args=["nonexistent-id"])


class TestRunAIModelsTask:
    """Test run_ai_models_task."""

    def test_run_ai_models_task_all_succeed(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test successful AI model execution."""
        with app.app_context():
            extraction_result = {
                "video_id": test_video.id,
                "frames": ["frame1.jpg", "frame2.jpg"],
                "audio_path": "audio.wav",
            }

            result = run_ai_models_task.apply(args=[extraction_result])

            assert result.successful()
            assert result.result["video_id"] == test_video.id
            assert result.result["llm_result"]["is_suspicious"] is True
            assert "ai_results" in result.result

            # Verify AI analysis called
            mock_orchestrator._run_parallel_ai_analysis.assert_called_once()

            # Verify LLM called
            mock_orchestrator.llm_analyzer.analyze_situation.assert_called_once()

            # Verify WebSocket events emitted
            mock_websocket["ai"].assert_called_once_with(test_video.id)
            mock_websocket["llm"].assert_called_once()

    def test_run_ai_models_task_partial_failure(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test task continues with partial AI failures."""
        with app.app_context():
            # Mock LLM to fail
            mock_orchestrator.llm_analyzer.analyze_situation.return_value = (None, Exception("LLM unavailable"))

            extraction_result = {
                "video_id": test_video.id,
                "frames": ["frame1.jpg"],
                "audio_path": None,
            }

            result = run_ai_models_task.apply(args=[extraction_result])

            assert result.successful()
            # Should use fallback analysis
            mock_orchestrator._fallback_analysis.assert_called_once()


class TestHandleSuspiciousResultTask:
    """Test handle_suspicious_result_task."""

    def test_handle_suspicious_result_task_suspicious(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test handling suspicious result creates ticket and sends alert."""
        with app.app_context():
            # Mock ticket creation
            from src.models.ticket import Ticket

            mock_ticket = Ticket(id="ticket-123", video_id=test_video.id)
            mock_orchestrator.ticket_service.create_ticket.return_value = (mock_ticket, None)
            mock_orchestrator.messenger_service.send_alert.return_value = (True, None)
            mock_orchestrator.storage_service.save_frame.return_value = (MagicMock(), None)
            mock_orchestrator.storage_service.save_audio.return_value = (MagicMock(), None)

            analysis_result = {
                "video_id": test_video.id,
                "llm_result": {
                    "is_suspicious": True,
                    "confidence": 0.92,
                    "threat_level": "high",
                },
                "ai_results": {"persons": []},
                "frames": ["frame1.jpg"],
                "audio_path": "audio.wav",
            }

            result = handle_suspicious_result_task.apply(args=[analysis_result])

            assert result.successful()
            assert result.result["is_suspicious"] is True
            assert result.result["ticket_id"] == "ticket-123"

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZED.value
            assert video.analysis_result == AnalysisResult.SUSPICIOUS.value

            # Verify WebSocket event emitted
            mock_websocket["complete"].assert_called_once()

    def test_handle_suspicious_result_task_clean(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test handling clean result doesn't create ticket."""
        with app.app_context():
            analysis_result = {
                "video_id": test_video.id,
                "llm_result": {
                    "is_suspicious": False,
                    "confidence": 0.88,
                },
                "ai_results": {},
                "frames": [],
                "audio_path": None,
            }

            result = handle_suspicious_result_task.apply(args=[analysis_result])

            assert result.successful()
            assert result.result["is_suspicious"] is False
            assert result.result["ticket_id"] is None

            # Verify no ticket created
            mock_orchestrator.ticket_service.create_ticket.assert_not_called()

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZED.value
            assert video.analysis_result == AnalysisResult.CLEAN.value

    def test_handle_suspicious_result_task_messenger_fails(self, app, test_video, mock_orchestrator, mock_websocket):
        """Test task continues even if messenger fails."""
        with app.app_context():
            from src.models.ticket import Ticket

            mock_ticket = Ticket(id="ticket-123", video_id=test_video.id)
            mock_orchestrator.ticket_service.create_ticket.return_value = (mock_ticket, None)
            mock_orchestrator.messenger_service.send_alert.return_value = (False, Exception("Telegram error"))

            analysis_result = {
                "video_id": test_video.id,
                "llm_result": {
                    "is_suspicious": True,
                    "confidence": 0.92,
                },
                "ai_results": {},
                "frames": [],
                "audio_path": None,
            }

            result = handle_suspicious_result_task.apply(args=[analysis_result])

            # Should still succeed (graceful degradation)
            assert result.successful()

            # Ticket should still be created
            mock_orchestrator.ticket_service.create_ticket.assert_called_once()

