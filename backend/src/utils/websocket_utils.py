import logging
import time
from datetime import datetime
from typing import Optional

from flask import request
from flask_jwt_extended import decode_token, verify_jwt_in_request
from flask_socketio import emit, disconnect

from src.app import socketio, jwt
from src.models.user import User

logger = logging.getLogger(__name__)


def emit_analysis_started(video_id: str) -> None:
    """Emit analysis_started event."""
    try:
        socketio.emit(
            "analysis_started",
            {"video_id": video_id, "timestamp": datetime.utcnow().isoformat()},
            namespace="/analysis",
        )
        logger.debug(f"Emitted analysis_started event for video {video_id}")
    except Exception as exc:
        logger.warning(f"Failed to emit analysis_started event: {exc}")


def emit_frames_extracted(video_id: str, frame_count: int) -> None:
    """Emit frames_extracted event."""
    try:
        socketio.emit(
            "frames_extracted",
            {
                "video_id": video_id,
                "frame_count": frame_count,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/analysis",
        )
        logger.debug(f"Emitted frames_extracted event for video {video_id}, frame_count: {frame_count}")
    except Exception as exc:
        logger.warning(f"Failed to emit frames_extracted event: {exc}")


def emit_ai_processing_started(video_id: str) -> None:
    """Emit ai_processing_started event."""
    try:
        socketio.emit(
            "ai_processing_started",
            {"video_id": video_id, "timestamp": datetime.utcnow().isoformat()},
            namespace="/analysis",
        )
        logger.debug(f"Emitted ai_processing_started event for video {video_id}")
    except Exception as exc:
        logger.warning(f"Failed to emit ai_processing_started event: {exc}")


def emit_llm_analysis_complete(video_id: str, is_suspicious: bool) -> None:
    """Emit llm_analysis_complete event."""
    try:
        socketio.emit(
            "llm_analysis_complete",
            {
                "video_id": video_id,
                "is_suspicious": is_suspicious,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/analysis",
        )
        logger.debug(f"Emitted llm_analysis_complete event for video {video_id}, is_suspicious: {is_suspicious}")
    except Exception as exc:
        logger.warning(f"Failed to emit llm_analysis_complete event: {exc}")


def emit_analysis_complete(
    video_id: str, result: str, ticket_id: Optional[str] = None, threat_level: Optional[str] = None
) -> None:
    """Emit analysis_complete event."""
    try:
        socketio.emit(
            "analysis_complete",
            {
                "video_id": video_id,
                "result": result,
                "ticket_id": ticket_id,
                "threat_level": threat_level,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/analysis",
        )
        logger.debug(
            f"Emitted analysis_complete event for video {video_id}, result: {result}, ticket_id: {ticket_id}"
        )
    except Exception as exc:
        logger.warning(f"Failed to emit analysis_complete event: {exc}")


def emit_analysis_error(video_id: str, error_message: str) -> None:
    """Emit analysis_error event."""
    try:
        socketio.emit(
            "analysis_error",
            {"video_id": video_id, "error": error_message, "timestamp": datetime.utcnow().isoformat()},
            namespace="/analysis",
        )
        logger.debug(f"Emitted analysis_error event for video {video_id}, error: {error_message}")
    except Exception as exc:
        logger.warning(f"Failed to emit analysis_error event: {exc}")


def emit_analysis_progress(video_id: str, stage: str, progress: int) -> None:
    """Emit analysis_progress event."""
    try:
        socketio.emit(
            "analysis_progress",
            {
                "video_id": video_id,
                "stage": stage,
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/analysis",
        )
        logger.debug(f"Emitted analysis_progress event for video {video_id}, stage: {stage}, progress: {progress}")
    except Exception as exc:
        logger.warning(f"Failed to emit analysis_progress event: {exc}")


# Local stream WebSocket handlers
@socketio.on("connect", namespace="/local-stream")
def handle_local_stream_connect(auth: dict) -> None:
    """Handle WebSocket connection for local stream namespace with JWT authentication."""
    try:
        token = auth.get("token") if isinstance(auth, dict) else None
        if not token:
            logger.warning("Local stream connection rejected: no token provided")
            disconnect()
            return

        # Decode and verify JWT token
        try:
            decoded_token = decode_token(token)
            user_id = decoded_token.get("sub")
            if not user_id:
                logger.warning("Local stream connection rejected: invalid token identity")
                disconnect()
                return

            user = User.query.get(user_id)
            if not user or not user.is_active or getattr(user, "is_deleted", False):
                logger.warning(f"Local stream connection rejected: inactive user {user_id}")
                disconnect()
                return

            logger.info(f"Local stream connection established for user {user_id}")
        except Exception as exc:
            logger.warning(f"Local stream connection rejected: token verification failed - {exc}")
            disconnect()
    except Exception as exc:
        logger.exception(f"Error during local stream connection: {exc}")
        disconnect()


@socketio.on("disconnect", namespace="/local-stream")
def handle_local_stream_disconnect() -> None:
    """Handle WebSocket disconnection for local stream namespace."""
    logger.info("Local stream client disconnected")


@socketio.on("frame_data", namespace="/local-stream")
def handle_frame_data(data: dict) -> None:
    """Handle incoming frame data from local stream client."""
    try:
        from src.services.local_stream_service import LocalStreamService

        service = LocalStreamService()
        session_id = data.get("session_id")
        frame_blob = data.get("frame")
        timestamp = data.get("timestamp", time.time())
        width = data.get("width")
        height = data.get("height")

        if not session_id or not frame_blob or not width or not height:
            emit_local_stream_error(session_id or "unknown", "Invalid frame data")
            return

        # Convert base64 string to bytes
        import base64
        if isinstance(frame_blob, str):
            # Remove data URL prefix if present
            if ',' in frame_blob:
                frame_blob = frame_blob.split(',')[1]
            frame_bytes = base64.b64decode(frame_blob)
        else:
            frame_bytes = frame_blob

        success, error = service.add_frame(session_id, frame_bytes, timestamp, width, height)
        if not success:
            emit_local_stream_error(session_id, error or "Failed to process frame")

    except Exception as exc:
        logger.exception(f"Error handling frame_data: {exc}")
        emit_local_stream_error(data.get("session_id", "unknown"), str(exc))


@socketio.on("stop_stream", namespace="/local-stream")
def handle_stop_stream(data: dict) -> None:
    """Handle stop stream request from local stream client."""
    try:
        from src.services.local_stream_service import LocalStreamService

        service = LocalStreamService()
        session_id = data.get("session_id")
        if not session_id:
            emit_local_stream_error("unknown", "Missing session_id")
            return

        success, error = service.stop_session(session_id)
        if not success:
            emit_local_stream_error(session_id, error or "Failed to stop session")
        else:
            socketio.emit(
                "stream_stopped",
                {"session_id": session_id, "timestamp": datetime.utcnow().isoformat()},
                namespace="/local-stream",
            )

    except Exception as exc:
        logger.exception(f"Error handling stop_stream: {exc}")
        emit_local_stream_error(data.get("session_id", "unknown"), str(exc))


def emit_local_stream_frame_ack(session_id: str, frame_id: Optional[str] = None) -> None:
    """Emit frame_ack event to local stream client."""
    try:
        socketio.emit(
            "frame_ack",
            {
                "session_id": session_id,
                "frame_id": frame_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/local-stream",
        )
        logger.debug(f"Emitted frame_ack for session {session_id}, frame_id: {frame_id}")
    except Exception as exc:
        logger.warning(f"Failed to emit frame_ack event: {exc}")


def emit_local_stream_error(session_id: str, error_message: str) -> None:
    """Emit error event to local stream client."""
    try:
        socketio.emit(
            "error",
            {
                "session_id": session_id,
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat(),
            },
            namespace="/local-stream",
        )
        logger.debug(f"Emitted error for session {session_id}: {error_message}")
    except Exception as exc:
        logger.warning(f"Failed to emit error event: {exc}")

