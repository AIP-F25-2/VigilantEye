import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, send_file
from src.app import db
from src.config.settings import get_config
from src.models.camera import Camera
from src.models.video import Video
from src.services.storage_service import (
    QuotaExceededError,
    StorageError,
    StorageService,
)
from src.services.video_processor import StreamError, VideoProcessorService
from src.utils.auth_middleware import get_current_user, require_auth


logger = logging.getLogger(__name__)

videos_bp = Blueprint("videos", __name__)
config = get_config()
video_processor = VideoProcessorService(config)
storage_service = StorageService(config)
SUPPORTED_VIDEO_FORMATS = {
    fmt.lower().lstrip(".") for fmt in config.SUPPORTED_VIDEO_FORMATS
}


@videos_bp.route("/upload", methods=["POST"])
@require_auth
def upload_video() -> Any:
    # Accept both "file" and "video" for backward compatibility
    file_obj = request.files.get("file") or request.files.get("video")
    if file_obj is None or not file_obj.filename:
        return jsonify({"error": "Invalid video file"}), 400

    camera_id = request.form.get("camera_id") or None
    if camera_id and not _is_valid_uuid(camera_id):
        return jsonify({"error": "Invalid camera identifier"}), 400

    extension = Path(file_obj.filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_VIDEO_FORMATS:
        return jsonify({"error": "Invalid video file"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    video, error = storage_service.save_video(
        file_obj,
        str(current_user.id),
        camera_id=camera_id,
        upload_type="upload",
    )
    if error:
        return _map_storage_error(error)

    video_path = video.get_storage_path() if video else None
    if video_path:
        is_valid, validation_error = video_processor.validate_video(video_path)
        if not is_valid:
            logger.error(
                "Video validation failed for %s: %s", video.id if video else None, validation_error
            )
            if video:
                deleted, delete_error = storage_service.delete_file(
                    video.id, "video", str(current_user.id), reason="validation_failed"
                )
                if not deleted and delete_error:
                    logger.error(
                        "Failed to cleanup invalid video %s: %s",
                        video.id,
                        delete_error,
                    )
            return jsonify({"error": validation_error or "Invalid video file"}), 400

    processed_video, processing_error = (
        video_processor.process_uploaded_video(video) if video else (None, None)
    )
    if processing_error:
        logger.warning(
            "Video processing encountered an error for %s: %s",
            video.id,
            processing_error,
        )

    response_video = processed_video or video
    return (
        jsonify(
            {
                "message": "Video uploaded successfully",
                "video": _serialize_video(response_video),
            }
        ),
        201,
    )


@videos_bp.route("/start-stream", methods=["POST"])
@require_auth
def start_stream() -> Any:
    payload = request.get_json(silent=True) or {}
    camera_id = payload.get("camera_id")
    stream_url = payload.get("stream_url")
    name = payload.get("name") or "Unnamed Camera"

    if not camera_id or not _is_valid_uuid(camera_id):
        return jsonify({"error": "Invalid camera identifier"}), 400
    if not stream_url:
        return jsonify({"error": "Invalid stream URL"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        camera = Camera.query.filter_by(id=camera_id, is_deleted=False).first()
        if camera is None:
            camera = Camera(id=camera_id, name=name, stream_url=stream_url)
            db.session.add(camera)
        else:
            camera.stream_url = stream_url
        camera.mark_active()

        video = Video(
            filename=f"live-stream-{camera_id}.mp4",
            filepath=f"streams/{camera_id}.stream",
            camera_id=camera_id,
            upload_type="stream",
            user_id=str(current_user.id),
        )
        video.mark_processing()
        video.set_video_ttl()
        db.session.add(video)
        db.session.flush()

        started, error = video_processor.start_stream(camera_id, stream_url)
        if error or not started:
            db.session.rollback()
            if isinstance(error, StreamError):
                message = str(error)
                if "maximum" in message.lower():
                    return jsonify({"error": message}), 429
                if "already" in message.lower():
                    return jsonify({"error": message}), 409
            return jsonify({"error": str(error) if error else "Failed to start stream"}), 500

        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Stream started successfully",
                    "camera_id": camera_id,
                    "video_id": video.id,
                    "status": "streaming",
                }
            ),
            201,
        )
    except Exception as exc:
        logger.exception("Failed to start stream for camera %s", camera_id)
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@videos_bp.route("/stop-stream", methods=["POST"])
@require_auth
def stop_stream() -> Any:
    payload = request.get_json(silent=True) or {}
    camera_id = payload.get("camera_id")
    if not camera_id or not _is_valid_uuid(camera_id):
        return jsonify({"error": "Invalid camera identifier"}), 400

    stopped, error = video_processor.stop_stream(camera_id)
    if error or not stopped:
        status = 404 if isinstance(error, StreamError) else 500
        return jsonify({"error": str(error) if error else "Failed to stop stream"}), status

    camera = Camera.query.filter_by(id=camera_id, is_deleted=False).first()
    if camera:
        camera.mark_inactive()

    active_video = (
        Video.query.filter_by(camera_id=camera_id, upload_type="stream", is_deleted=False)
        .order_by(Video.created_at.desc())
        .first()
    )
    if active_video:
        active_video.mark_ready()

    db.session.commit()
    return jsonify({"message": "Stream stopped successfully", "camera_id": camera_id}), 200


@videos_bp.route("/", methods=["GET"])
@require_auth
def list_videos() -> Any:
    args = request.args
    try:
        page = max(int(args.get("page", 1)), 1)
        per_page = min(int(args.get("per_page", 20)), 100)
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    status_filter = args.get("status")
    camera_filter = args.get("camera_id")
    upload_type_filter = args.get("upload_type")

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    query = Video.query.filter_by(is_deleted=False)
    if current_user.role != "admin":
        query = query.filter_by(user_id=str(current_user.id))

    if status_filter:
        query = query.filter_by(status=status_filter)
    if camera_filter:
        query = query.filter_by(camera_id=camera_filter)
    if upload_type_filter:
        query = query.filter_by(upload_type=upload_type_filter)

    query = query.order_by(Video.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    videos = [_serialize_video(video) for video in pagination.items]
    return jsonify(
        {
            "videos": videos,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }
    )


@videos_bp.route("/<video_id>", methods=["GET"])
@require_auth
def get_video(video_id: str) -> Any:
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    video = Video.query.filter_by(id=video_id, is_deleted=False).first()
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    if current_user.role != "admin" and str(video.user_id) != str(current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    return jsonify({"video": _serialize_video(video, include_thumbnail=True)}), 200


@videos_bp.route("/<video_id>/thumbnail", methods=["GET"])
@require_auth
def get_thumbnail(video_id: str) -> Any:
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    video = Video.query.filter_by(id=video_id, is_deleted=False).first()
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    if current_user.role != "admin" and str(video.user_id) != str(current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    storage_path = Path(video.get_storage_path())
    thumbnail_path = storage_path.with_name(f"{storage_path.stem}-thumb.jpg")
    if not thumbnail_path.exists():
        return jsonify({"error": "Thumbnail not found"}), 404

    return send_file(str(thumbnail_path), mimetype="image/jpeg")


@videos_bp.route("/<video_id>/analyze", methods=["POST"])
@require_auth
def analyze_video(video_id: str) -> Any:
    """Trigger video analysis."""
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    video = Video.query.filter_by(id=video_id, is_deleted=False).first_or_404()
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    # Check authorization
    if current_user.role != "admin" and str(video.user_id) != str(current_user.id):
        return jsonify({"error": "Forbidden - Not authorized to analyze this video"}), 403

    # Validate video status
    from src.config.constants import VideoStatus

    if video.status == VideoStatus.ANALYZING.value:
        return jsonify({"error": "Video is already being analyzed"}), 409

    if video.status == VideoStatus.ANALYZED.value:
        # Return existing result
        from src.models.ticket import Ticket

        ticket = Ticket.query.filter_by(video_id=video_id).order_by(Ticket.created_at.desc()).first()
        return (
            jsonify(
                {
                    "message": "Video already analyzed",
                    "video_id": video_id,
                    "status": video.status,
                    "analysis_result": video.analysis_result,
                    "ticket_id": ticket.id if ticket else None,
                }
            ),
            200,
        )

    if video.status != VideoStatus.READY.value:
        return jsonify({"error": "Video not ready for analysis"}), 400

    # Import and trigger Celery task
    from src.tasks import analyze_video_task

    task = analyze_video_task.delay(video_id)

    # Update video status
    video.mark_analyzing()
    db.session.commit()

    # Create audit log
    from src.models.audit_log import AuditLog

    audit_log = AuditLog(
        action="video_analysis_triggered",
        resource_type="video",
        resource_id=video_id,
        user_id=str(current_user.id),
        details={"task_id": task.id},
    )
    db.session.add(audit_log)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Video analysis started",
                "video_id": video_id,
                "task_id": task.id,
                "status": "analyzing",
            }
        ),
        202,
    )


@videos_bp.route("/<video_id>/analysis-status", methods=["GET"])
@require_auth
def get_analysis_status(video_id: str) -> Any:
    """Get current analysis status and results."""
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    video = Video.query.filter_by(id=video_id, is_deleted=False).first_or_404()
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    # Check authorization
    if current_user.role != "admin" and str(video.user_id) != str(current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    # Get ticket if suspicious
    ticket_id = None
    if video.analysis_result == "suspicious":
        from src.models.ticket import Ticket

        ticket = Ticket.query.filter_by(video_id=video_id).order_by(Ticket.created_at.desc()).first()
        if ticket:
            ticket_id = ticket.id

    return (
        jsonify(
            {
                "video_id": video_id,
                "status": video.status,
                "analysis_result": video.analysis_result,
                "ticket_id": ticket_id,
                "analyzed_at": video.analysis_completed_at.isoformat() if video.analysis_completed_at else None,
            }
        ),
        200,
    )


@videos_bp.route("/streams/active", methods=["GET"])
@require_auth
def get_active_streams() -> Any:
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    with video_processor.streams_lock:
        active_snapshot = {
            camera_id: info.copy() for camera_id, info in video_processor.active_streams.items()
        }

    streams: List[Dict[str, Any]] = []
    for camera_id, stream_info in active_snapshot.items():
        camera = Camera.query.filter_by(id=camera_id, is_deleted=False).first()
        video = (
            Video.query.filter_by(camera_id=camera_id, upload_type="stream", is_deleted=False)
            .order_by(Video.created_at.desc())
            .first()
        )
        streams.append(
            {
                "camera_id": camera_id,
                "camera_name": camera.name if camera else None,
                "stream_url": camera.stream_url if camera else stream_info.get("stream_url"),
                "video_id": video.id if video else None,
                "started_at": stream_info.get("started_at").isoformat()
                if stream_info.get("started_at")
                else None,
            }
        )

    return jsonify(
        {
            "active_streams": streams,
            "count": len(streams),
            "max_streams": config.MAX_CONCURRENT_STREAMS,
        }
    )


def _serialize_video(video: Optional[Video], include_thumbnail: bool = False) -> Optional[Dict[str, Any]]:
    if video is None:
        return None

    data: Dict[str, Any] = {
        "id": video.id,
        "filename": video.filename,
        "status": video.status,
        "duration": video.duration,
        "fps": video.fps,
        "resolution": video.resolution,
        "upload_type": video.upload_type,
        "camera_id": video.camera_id,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "expires_at": video.expires_at.isoformat() if video.expires_at else None,
        "analysis_result": video.analysis_result,
    }

    if include_thumbnail:
        data["thumbnail_url"] = f"/api/videos/{video.id}/thumbnail"

    if video.filepath:
        data["filepath"] = video.filepath

    return data


def _map_storage_error(error: Exception):
    if isinstance(error, QuotaExceededError):
        message = str(error) or "Storage quota exceeded"
        if "size" in message.lower():
            return jsonify({"error": message}), 413
        return jsonify({"error": message}), 409
    if isinstance(error, StorageError):
        message = str(error) or "Storage operation failed"
        if "unsupported video format" in message.lower():
            return jsonify({"error": "Invalid video file"}), 400
        return jsonify({"error": message}), 400
    return jsonify({"error": "Internal server error"}), 500


@videos_bp.route("/start-local-stream", methods=["POST"])
@require_auth
def start_local_stream() -> Any:
    """Start a local camera stream session."""
    payload = request.get_json(silent=True) or {}
    camera_name = payload.get("camera_name") or "Local Camera"

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        from src.services.local_stream_service import LocalStreamService

        service = LocalStreamService()
        session_id, video_id, error = service.create_session(
            user_id=str(current_user.id), camera_name=camera_name
        )

        if error:
            if "maximum" in error.lower():
                return jsonify({"error": error}), 429
            return jsonify({"error": error}), 500

        if not session_id or not video_id:
            return jsonify({"error": "Failed to create stream session"}), 500

        return (
            jsonify(
                {
                    "message": "Local stream session created",
                    "stream_session_id": session_id,
                    "video_id": video_id,
                    "status": "streaming",
                }
            ),
            201,
        )
    except Exception as exc:
        logger.exception("Failed to start local stream")
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@videos_bp.route("/stop-local-stream", methods=["POST"])
@require_auth
def stop_local_stream() -> Any:
    """Stop a local camera stream session."""
    payload = request.get_json(silent=True) or {}
    stream_session_id = payload.get("stream_session_id")

    if not stream_session_id:
        return jsonify({"error": "stream_session_id is required"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        from src.services.local_stream_service import LocalStreamService

        service = LocalStreamService()
        session = service.get_session(stream_session_id)
        if session and session.get("user_id") != str(current_user.id):
            return jsonify({"error": "Forbidden"}), 403

        success, error = service.stop_session(stream_session_id)
        if error:
            return jsonify({"error": error}), 500

        return jsonify({"message": "Local stream stopped successfully"}), 200
    except Exception as exc:
        logger.exception("Failed to stop local stream")
        return jsonify({"error": str(exc)}), 500


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
