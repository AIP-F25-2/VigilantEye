import mimetypes
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request, send_file

from src.models.evidence import Evidence
from src.models.ticket import Ticket
from src.models.video import Video
from src.services.storage_service import (
    QuotaExceededError,
    StorageError,
    StorageFileNotFoundError,
    StorageService,
)
from src.tasks.cleanup_task import cleanup_expired_files
from src.utils.auth_middleware import admin_only, get_current_user, require_auth

storage_bp = Blueprint("storage", __name__)
storage_service = StorageService()


@storage_bp.route("/videos/<video_id>", methods=["DELETE"])
@admin_only
def delete_video(video_id: str):
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    admin_user = get_current_user()
    reason = _extract_reason(request.get_json(silent=True))

    success, error = storage_service.delete_file(video_id, "video", admin_user.id, reason)
    if error:
        return _handle_storage_error(error)
    if not success:
        return jsonify({"error": "Failed to delete video"}), 500

    return jsonify({"message": "Video deleted successfully", "video_id": video_id}), 200


@storage_bp.route("/evidence/<evidence_id>", methods=["DELETE"])
@admin_only
def delete_evidence(evidence_id: str):
    if not _is_valid_uuid(evidence_id):
        return jsonify({"error": "Invalid evidence identifier"}), 400

    admin_user = get_current_user()
    reason = _extract_reason(request.get_json(silent=True))

    success, error = storage_service.delete_file(
        evidence_id, "evidence", admin_user.id, reason
    )
    if error:
        return _handle_storage_error(error)
    if not success:
        return jsonify({"error": "Failed to delete evidence"}), 500

    return (
        jsonify({"message": "Evidence deleted successfully", "evidence_id": evidence_id}),
        200,
    )


@storage_bp.route("/quota/user/<user_id>", methods=["GET"])
@require_auth
def get_user_quota(user_id: str):
    if not _is_valid_uuid(user_id):
        return jsonify({"error": "Invalid user identifier"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    if current_user.role != "admin" and str(current_user.id) != user_id:
        return jsonify({"error": "Forbidden - Cannot view other user's quota"}), 403

    quota, error = storage_service.get_user_quota(user_id)
    if error:
        return _handle_storage_error(error)
    if quota is None:
        return jsonify({"error": "Quota information unavailable"}), 404

    response = {
        **quota,
        "used_human": _format_bytes(quota["used_bytes"]),
        "max_human": _format_bytes(quota["max_bytes"]),
    }
    return jsonify(response), 200


@storage_bp.route("/quota/system", methods=["GET"])
@admin_only
def get_system_quota():
    quota, error = storage_service.get_system_quota()
    if error:
        return _handle_storage_error(error)
    if quota is None:
        return jsonify({"error": "System quota unavailable"}), 404

    response = {
        **quota,
        "used_human": _format_bytes(quota["used_bytes"]),
        "total_human": _format_bytes(quota["total_bytes"]),
        "free_human": _format_bytes(quota["free_bytes"]),
    }
    return jsonify(response), 200


@storage_bp.route("/videos/<video_id>/download", methods=["GET"])
@require_auth
def download_video(video_id: str):
    if not _is_valid_uuid(video_id):
        return jsonify({"error": "Invalid video identifier"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    video = Video.query.filter_by(id=video_id, is_deleted=False).first()
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    if current_user.role != "admin" and video.user_id != current_user.id:
        return jsonify({"error": "Forbidden - Not authorized to download this video"}), 403

    filepath, error = storage_service.get_file_path(video_id, "video")
    if error:
        return _handle_storage_error(error)
    if filepath is None:
        return jsonify({"error": "Video file not available"}), 404

    mime_type, _ = mimetypes.guess_type(video.filename or "")
    download_name = video.filename or Path(filepath).name
    return send_file(
        filepath,
        mimetype=mime_type,
        as_attachment=True,
        download_name=download_name,
        conditional=True,
    )


@storage_bp.route("/evidence/<evidence_id>/download", methods=["GET"])
@require_auth
def download_evidence(evidence_id: str):
    if not _is_valid_uuid(evidence_id):
        return jsonify({"error": "Invalid evidence identifier"}), 400

    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized"}), 401

    evidence = Evidence.query.filter_by(id=evidence_id, is_deleted=False).first()
    if evidence is None:
        return jsonify({"error": "Evidence not found"}), 404

    if current_user.role != "admin":
        ticket = evidence.ticket
        if ticket is None:
            return jsonify({"error": "Forbidden - Ticket unavailable"}), 403
        if ticket.assigned_to != current_user.id:
            return jsonify(
                {"error": "Forbidden - Not authorized to download this evidence"}
            ), 403

    filepath, error = storage_service.get_file_path(evidence_id, "evidence")
    if error:
        return _handle_storage_error(error)
    if filepath is None:
        return jsonify({"error": "Evidence file not available"}), 404

    filename = Path(filepath).name
    mime_type, _ = mimetypes.guess_type(filename)
    return send_file(
        filepath,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
        conditional=True,
    )


@storage_bp.route("/cleanup/trigger", methods=["POST"])
@admin_only
def trigger_cleanup():
    task = cleanup_expired_files.delay()
    return (
        jsonify({"message": "Cleanup task triggered", "task_id": str(task.id)}),
        202,
    )


def _handle_storage_error(error: Exception):
    if isinstance(error, QuotaExceededError):
        return jsonify({"error": str(error)}), 413
    if isinstance(error, StorageFileNotFoundError):
        return jsonify({"error": str(error)}), 404
    if isinstance(error, StorageError):
        message = str(error) or "Storage operation failed"
        if "not found" in message.lower():
            return jsonify({"error": message}), 404
        if "cannot delete" in message.lower():
            return jsonify({"error": message}), 409
        return jsonify({"error": message}), 400
    return jsonify({"error": "Internal server error"}), 500


def _format_bytes(size: int) -> str:
    if size is None:
        return "0 B"
    power = 1024
    n = 0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _extract_reason(payload: Dict[str, Any] | None) -> str:
    if not payload:
        return "Deleted by admin"
    reason = payload.get("reason") if isinstance(payload, dict) else None
    if not reason:
        return "Deleted by admin"
    reason_str = str(reason).strip()
    if len(reason_str) > 500:
        return reason_str[:500]
    return reason_str


