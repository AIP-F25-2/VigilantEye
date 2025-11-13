import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from flask_jwt_extended import create_access_token

from src.app import create_app, db
from src.config.constants import AnalysisResult, UserRole, VideoStatus
from src.models.user import User
from src.models.video import Video


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
def admin_user(app):
    with app.app_context():
        user = User(username="admin1", email="admin1@test.com", role=UserRole.ADMIN, is_active=True)
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
def access_token_staff(app, staff_user):
    with app.app_context():
        return create_access_token(identity=str(staff_user.id))


@pytest.fixture
def access_token_admin(app, admin_user):
    with app.app_context():
        return create_access_token(identity=str(admin_user.id))


class TestAnalyzeVideoEndpoint:
    """Test POST /api/videos/{video_id}/analyze endpoint."""

    def test_analyze_video_endpoint_success(self, app, test_video, access_token_staff):
        """Test successful video analysis trigger."""
        with app.app_context(), patch("src.tasks.analysis_tasks.analyze_video_task") as mock_task:
            mock_task_instance = MagicMock()
            mock_task_instance.id = "task-123"
            mock_task.delay.return_value = mock_task_instance

            client = app.test_client()
            response = client.post(
                f"/api/videos/{test_video.id}/analyze",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 202
            data = response.get_json()
            assert data["message"] == "Video analysis started"
            assert data["video_id"] == test_video.id
            assert data["task_id"] == "task-123"
            assert data["status"] == "analyzing"

            # Verify task called
            mock_task.delay.assert_called_once_with(test_video.id)

            # Verify video status updated
            video = Video.query.get(test_video.id)
            assert video.status == VideoStatus.ANALYZING.value

    def test_analyze_video_endpoint_without_auth(self, app, test_video):
        """Test endpoint requires authentication."""
        client = app.test_client()
        response = client.post(f"/api/videos/{test_video.id}/analyze")

        assert response.status_code == 401

    def test_analyze_video_endpoint_not_owner_as_staff(self, app, staff_user, access_token_staff):
        """Test staff user cannot analyze other user's video."""
        with app.app_context():
            # Create video owned by different user
            other_user = User(username="staff2", email="staff2@test.com", role=UserRole.STAFF, is_active=True)
            other_user.set_password("password123")
            db.session.add(other_user)
            db.session.commit()

            other_video = Video(
                filename="other_video.mp4",
                filepath="videos/other_video.mp4",
                user_id=str(other_user.id),
                upload_type="upload",
                status=VideoStatus.READY.value,
            )
            db.session.add(other_video)
            db.session.commit()

            client = app.test_client()
            response = client.post(
                f"/api/videos/{other_video.id}/analyze",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 403
            data = response.get_json()
            assert "Forbidden" in data["error"]

    def test_analyze_video_endpoint_not_owner_as_admin(self, app, staff_user, admin_user, access_token_admin):
        """Test admin can analyze any video."""
        with app.app_context():
            video = Video(
                filename="staff_video.mp4",
                filepath="videos/staff_video.mp4",
                user_id=str(staff_user.id),
                upload_type="upload",
                status=VideoStatus.READY.value,
            )
            db.session.add(video)
            db.session.commit()

            with patch("src.tasks.analysis_tasks.analyze_video_task") as mock_task:
                mock_task_instance = MagicMock()
                mock_task_instance.id = "task-123"
                mock_task.delay.return_value = mock_task_instance

                client = app.test_client()
                response = client.post(
                    f"/api/videos/{video.id}/analyze",
                    headers={"Authorization": f"Bearer {access_token_admin}"},
                )

                assert response.status_code == 202

    def test_analyze_video_endpoint_already_analyzing(self, app, test_video, access_token_staff):
        """Test endpoint returns 409 when video is already analyzing."""
        with app.app_context():
            test_video.mark_analyzing()
            db.session.commit()

            client = app.test_client()
            response = client.post(
                f"/api/videos/{test_video.id}/analyze",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 409
            data = response.get_json()
            assert "already being analyzed" in data["error"]

    def test_analyze_video_endpoint_already_analyzed(self, app, test_video, access_token_staff):
        """Test endpoint returns existing result when video already analyzed."""
        with app.app_context():
            from src.config.constants import AnalysisResult

            test_video.mark_analyzed(AnalysisResult.CLEAN)
            db.session.commit()

            client = app.test_client()
            response = client.post(
                f"/api/videos/{test_video.id}/analyze",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["message"] == "Video already analyzed"
            assert data["analysis_result"] == AnalysisResult.CLEAN.value

    def test_analyze_video_endpoint_video_not_ready(self, app, staff_user, access_token_staff):
        """Test endpoint returns 400 when video not ready."""
        with app.app_context():
            video = Video(
                filename="uploading_video.mp4",
                filepath="videos/uploading_video.mp4",
                user_id=str(staff_user.id),
                upload_type="upload",
                status=VideoStatus.UPLOADING.value,
            )
            db.session.add(video)
            db.session.commit()

            client = app.test_client()
            response = client.post(
                f"/api/videos/{video.id}/analyze",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 400
            data = response.get_json()
            assert "not ready" in data["error"]


class TestGetAnalysisStatusEndpoint:
    """Test GET /api/videos/{video_id}/analysis-status endpoint."""

    def test_get_analysis_status_analyzing(self, app, test_video, access_token_staff):
        """Test get status when video is analyzing."""
        with app.app_context():
            test_video.mark_analyzing()
            db.session.commit()

            client = app.test_client()
            response = client.get(
                f"/api/videos/{test_video.id}/analysis-status",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == VideoStatus.ANALYZING.value

    def test_get_analysis_status_analyzed_suspicious(self, app, test_video, access_token_staff):
        """Test get status when video analyzed as suspicious."""
        with app.app_context():
            from src.models.ticket import Ticket

            test_video.mark_analyzed(AnalysisResult.SUSPICIOUS)
            db.session.commit()

            ticket = Ticket(
                video_id=test_video.id,
                title="Test ticket",
                threat_level="high",
                priority="high",
            )
            db.session.add(ticket)
            db.session.commit()

            client = app.test_client()
            response = client.get(
                f"/api/videos/{test_video.id}/analysis-status",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == VideoStatus.ANALYZED.value
            assert data["analysis_result"] == AnalysisResult.SUSPICIOUS.value
            assert data["ticket_id"] == ticket.id

    def test_get_analysis_status_analyzed_clean(self, app, test_video, access_token_staff):
        """Test get status when video analyzed as clean."""
        with app.app_context():
            test_video.mark_analyzed(AnalysisResult.CLEAN)
            test_video.analysis_completed_at = datetime.utcnow()
            db.session.commit()

            client = app.test_client()
            response = client.get(
                f"/api/videos/{test_video.id}/analysis-status",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == VideoStatus.ANALYZED.value
            assert data["analysis_result"] == AnalysisResult.CLEAN.value
            assert data["ticket_id"] is None
            assert data["analyzed_at"] is not None

    def test_get_analysis_status_error(self, app, test_video, access_token_staff):
        """Test get status when video has error."""
        with app.app_context():
            test_video.mark_error("Analysis failed")
            db.session.commit()

            client = app.test_client()
            response = client.get(
                f"/api/videos/{test_video.id}/analysis-status",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == VideoStatus.ERROR.value

    def test_get_analysis_status_forbidden(self, app, staff_user, access_token_staff):
        """Test get status returns 403 for non-owner."""
        with app.app_context():
            other_user = User(username="staff2", email="staff2@test.com", role=UserRole.STAFF, is_active=True)
            other_user.set_password("password123")
            db.session.add(other_user)
            db.session.commit()

            other_video = Video(
                filename="other_video.mp4",
                filepath="videos/other_video.mp4",
                user_id=str(other_user.id),
                upload_type="upload",
                status=VideoStatus.READY.value,
            )
            db.session.add(other_video)
            db.session.commit()

            client = app.test_client()
            response = client.get(
                f"/api/videos/{other_video.id}/analysis-status",
                headers={"Authorization": f"Bearer {access_token_staff}"},
            )

            assert response.status_code == 403

