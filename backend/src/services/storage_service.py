import hashlib
import logging
import os
import shutil
import uuid
from builtins import FileNotFoundError as BuiltinFileNotFoundError
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import redis
from flask import g, has_request_context, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.app import db
from src.config import BaseConfig, get_config
from src.models.audit_log import AuditLog
from src.models.evidence import Evidence
from src.models.ticket import Ticket
from src.models.video import Video

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""


class QuotaExceededError(StorageError):
    """Raised when a quota limit is exceeded."""


class StorageFileNotFoundError(StorageError):
    """Raised when a file cannot be located on disk."""


class StorageService:
    """Manage persistence of media assets and associated metadata."""

    _instance: Optional["StorageService"] = None
    _initialized: bool = False

    def __new__(cls, config: Optional[BaseConfig] = None) -> "StorageService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[BaseConfig] = None) -> None:
        if self.__class__._initialized:
            return

        self.config = config or get_config()
        self.storage_base_path = Path(self.config.STORAGE_BASE_PATH).resolve()
        self.max_video_size_bytes = self.config.MAX_VIDEO_SIZE_MB * 1024 * 1024
        self.supported_video_formats = {
            fmt.lower().lstrip(".") for fmt in self.config.SUPPORTED_VIDEO_FORMATS
        }
        self.redis_client = redis.from_url(self.config.REDIS_URL)

        self._ensure_storage_directories()

        self.__class__._initialized = True
        logger.debug(
            "StorageService initialized",
            extra={
                "context": {
                    "storage_base_path": str(self.storage_base_path),
                    "max_video_size_bytes": self.max_video_size_bytes,
                    "supported_formats": list(self.supported_video_formats),
                }
            },
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def save_video(
        self,
        file_obj: FileStorage,
        user_id: str,
        camera_id: Optional[str] = None,
        upload_type: str = "upload",
    ) -> Tuple[Optional[Video], Optional[Exception]]:
        """Persist an uploaded video to disk and database."""
        try:
            if file_obj is None or file_obj.filename is None:
                raise StorageError("Invalid video upload request")

            original_filename = secure_filename(file_obj.filename)
            if not original_filename:
                raise StorageError("Invalid video filename")

            extension = Path(original_filename).suffix.lower().lstrip(".")
            if extension not in self.supported_video_formats:
                raise StorageError(f"Unsupported video format: .{extension}")

            content_length = getattr(file_obj, "content_length", None)
            if content_length is None:
                position = file_obj.stream.tell()
                file_obj.stream.seek(0, os.SEEK_END)
                content_length = file_obj.stream.tell()
                file_obj.stream.seek(position)
            if content_length and content_length > self.max_video_size_bytes:
                raise QuotaExceededError("Video exceeds maximum allowed size")

            quota_info, quota_error = self.get_user_quota(user_id)
            if quota_error:
                raise quota_error
            if quota_info and content_length is not None:
                max_bytes = quota_info.get("max_bytes")
                proposed_usage = quota_info["used_bytes"] + content_length
                if max_bytes is not None and max_bytes >= 0 and proposed_usage > max_bytes:
                    raise QuotaExceededError("User storage quota exceeded")

            target_dir = self._build_video_directory(datetime.utcnow())
            target_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4()}.{extension}"
            absolute_path = target_dir / filename
            relative_path = absolute_path.relative_to(self.storage_base_path)

            checksum, bytes_written = self._write_file_stream(file_obj, absolute_path)

            video = Video(
                filename=original_filename,
                filepath=str(relative_path).replace("\\", "/"),
                camera_id=camera_id,
                upload_type=upload_type,
                user_id=user_id,
                filesize=bytes_written,
                checksum=checksum,
            )
            video.set_video_ttl()

            db.session.add(video)
            db.session.flush()

            db.session.commit()

            try:
                self._update_user_quota(user_id, bytes_written)
                self._increment_system_usage(bytes_written)
            except Exception as quota_exc:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to update quota after video upload",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "bytes_written": bytes_written,
                            "error": str(quota_exc),
                        }
                    },
                )

            audit_log = self._create_audit_log(
                user_id=user_id,
                action="video_uploaded",
                resource_type="video",
                resource_id=video.id,
                details={
                    "filename": original_filename,
                    "filesize": bytes_written,
                    "checksum": checksum,
                    "upload_type": upload_type,
                },
            )
            if audit_log is not None:
                try:
                    db.session.commit()
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    logger.warning(
                        "Failed to persist audit log for video upload",
                        extra={
                            "context": {
                                "video_id": video.id,
                                "user_id": user_id,
                                "error": str(exc),
                            }
                        },
                    )

            return video, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to save video",
                extra={"context": {"user_id": user_id, "error": str(exc)}},
            )
            db.session.rollback()
            self._safe_remove_path(locals().get("absolute_path"))
            return None, exc

    def save_frame(
        self,
        frame_data: bytes,
        ticket_id: str,
        video_id: Optional[str],
        timestamp: datetime,
        frame_number: int,
        description: Optional[str] = None,
    ) -> Tuple[Optional[Evidence], Optional[Exception]]:
        """Persist a frame extracted from a video."""
        try:
            if not frame_data:
                raise StorageError("Frame data is empty")

            filename = f"{uuid.uuid4()}.jpg"
            target_dir = self.storage_base_path / "evidence" / str(ticket_id)
            target_dir.mkdir(parents=True, exist_ok=True)
            absolute_path = target_dir / filename
            relative_path = absolute_path.relative_to(self.storage_base_path)

            checksum = self._write_binary(absolute_path, frame_data)

            evidence = Evidence(
                video_id=video_id,
                ticket_id=ticket_id,
                type="frame",
                filepath=str(relative_path).replace("\\", "/"),
                timestamp=timestamp,
                frame_number=frame_number,
                description=description,
                checksum=checksum,
            )
            db.session.add(evidence)
            db.session.flush()
            db.session.commit()

            audit_log = self._create_audit_log(
                user_id=self._get_request_user_id(),
                action="frame_saved",
                resource_type="evidence",
                resource_id=evidence.id,
                details={
                    "ticket_id": ticket_id,
                    "video_id": video_id,
                    "frame_number": frame_number,
                    "checksum": checksum,
                },
            )
            if audit_log is not None:
                try:
                    db.session.commit()
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    logger.warning(
                        "Failed to persist audit log for frame evidence",
                        extra={
                            "context": {
                                "evidence_id": evidence.id,
                                "ticket_id": ticket_id,
                                "error": str(exc),
                            }
                        },
                    )

            return evidence, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to save frame",
                extra={
                    "context": {
                        "ticket_id": ticket_id,
                        "video_id": video_id,
                        "error": str(exc),
                    }
                },
            )
            db.session.rollback()
            self._safe_remove_path(locals().get("absolute_path"))
            return None, exc

    def save_audio(
        self,
        audio_data: bytes,
        ticket_id: str,
        video_id: Optional[str],
        timestamp: datetime,
        description: Optional[str] = None,
    ) -> Tuple[Optional[Evidence], Optional[Exception]]:
        """Persist audio evidence extracted from a video."""
        try:
            if not audio_data:
                raise StorageError("Audio data is empty")

            filename = f"{uuid.uuid4()}.wav"
            target_dir = self.storage_base_path / "evidence" / str(ticket_id)
            target_dir.mkdir(parents=True, exist_ok=True)
            absolute_path = target_dir / filename
            relative_path = absolute_path.relative_to(self.storage_base_path)

            checksum = self._write_binary(absolute_path, audio_data)

            evidence = Evidence(
                video_id=video_id,
                ticket_id=ticket_id,
                type="audio",
                filepath=str(relative_path).replace("\\", "/"),
                timestamp=timestamp,
                description=description,
                checksum=checksum,
            )
            db.session.add(evidence)
            db.session.flush()
            db.session.commit()

            audit_log = self._create_audit_log(
                user_id=self._get_request_user_id(),
                action="audio_saved",
                resource_type="evidence",
                resource_id=evidence.id,
                details={
                    "ticket_id": ticket_id,
                    "video_id": video_id,
                    "checksum": checksum,
                },
            )
            if audit_log is not None:
                try:
                    db.session.commit()
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    logger.warning(
                        "Failed to persist audit log for audio evidence",
                        extra={
                            "context": {
                                "evidence_id": evidence.id,
                                "ticket_id": ticket_id,
                                "error": str(exc),
                            }
                        },
                    )

            return evidence, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to save audio",
                extra={
                    "context": {
                        "ticket_id": ticket_id,
                        "video_id": video_id,
                        "error": str(exc),
                    }
                },
            )
            db.session.rollback()
            self._safe_remove_path(locals().get("absolute_path"))
            return None, exc

    def delete_file(
        self, file_id: str, file_type: str, user_id: str, reason: Optional[str] = None
    ) -> Tuple[bool, Optional[Exception]]:
        """Soft delete metadata and remove the file from disk."""
        try:
            record = self._get_record(file_id, file_type)
            if record is None:
                raise StorageError(f"{file_type.capitalize()} not found")

            dependency_error = self._check_dependencies(record, file_type)
            if dependency_error:
                return False, dependency_error

            previous_deleted_state = getattr(record, "is_deleted", False)
            record.soft_delete()
            filepath = record.get_storage_path()
            filesize = getattr(record, "filesize", 0) or 0

            db.session.flush()

            self._safe_remove_path(filepath)

            if file_type == "video" and filesize:
                self._update_user_quota(record.user_id, -filesize)
                self._increment_system_usage(-filesize)

            db.session.commit()

            audit_log = self._create_audit_log(
                user_id=user_id,
                action="file_deleted",
                resource_type=file_type,
                resource_id=file_id,
                details={
                    "reason": reason or "Deleted by administrator",
                    "previously_deleted": previous_deleted_state,
                },
            )
            if audit_log is not None:
                try:
                    db.session.commit()
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    logger.warning(
                        "Failed to persist audit log for file deletion",
                        extra={
                            "context": {
                                "resource_type": file_type,
                                "resource_id": file_id,
                                "error": str(exc),
                            }
                        },
                    )
            return True, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to delete file",
                extra={
                    "context": {
                        "file_id": file_id,
                        "file_type": file_type,
                        "user_id": user_id,
                        "error": str(exc),
                    }
                },
            )
            db.session.rollback()
            return False, exc

    def get_file_path(
        self, file_id: str, file_type: str
    ) -> Tuple[Optional[str], Optional[Exception]]:
        """Resolve and validate the absolute path for a stored file."""
        try:
            record = self._get_record(file_id, file_type)
            if record is None or getattr(record, "is_deleted", False):
                raise StorageError(f"{file_type.capitalize()} not found")

            filepath = record.get_storage_path()
            if not os.path.exists(filepath):
                raise StorageFileNotFoundError(f"File missing on disk: {filepath}")

            audit_log = self._create_audit_log(
                user_id=self._get_request_user_id(),
                action="file_accessed",
                resource_type=file_type,
                resource_id=file_id,
                details={"path": filepath},
            )
            if audit_log is not None:
                try:
                    db.session.commit()
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    logger.warning(
                        "Failed to persist audit log for file access",
                        extra={
                            "context": {
                                "resource_type": file_type,
                                "resource_id": file_id,
                                "error": str(exc),
                            }
                        },
                    )

            return filepath, None
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to resolve file path",
                extra={
                    "context": {
                        "file_id": file_id,
                        "file_type": file_type,
                        "error": str(exc),
                    }
                },
            )
            return None, exc

    def get_user_quota(self, user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """Retrieve quota usage for a specific user."""
        try:
            cache_key = f"quota:user:{user_id}"
            quota_data = self.redis_client.hgetall(cache_key)
            if quota_data:
                used_bytes = int(self._decode_redis_value(quota_data.get("used_bytes", b"0")))
            else:
                used_bytes = self._calculate_user_quota_from_db(user_id)
                self.redis_client.hset(
                    cache_key,
                    mapping={"used_bytes": used_bytes, "updated_at": datetime.utcnow().isoformat()},
                )

            max_bytes = self.config.USER_QUOTA_MAX_BYTES
            percentage = min((used_bytes / max_bytes) * 100 if max_bytes else 0, 100.0)

            return (
                {
                    "user_id": user_id,
                    "used_bytes": used_bytes,
                    "max_bytes": max_bytes,
                    "percentage": round(percentage, 2),
                },
                None,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Failed to retrieve user quota",
                extra={"context": {"user_id": user_id, "error": str(exc)}},
            )
            return None, exc

    def get_system_quota(self) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """Aggregate system-wide storage usage."""
        try:
            used_bytes = self._get_system_usage()
            total_bytes, _, free_bytes = shutil.disk_usage(self.storage_base_path)
            percentage = round((used_bytes / total_bytes) * 100, 2) if total_bytes else 0.0

            breakdown = self._calculate_storage_breakdown()

            return (
                {
                    "used_bytes": used_bytes,
                    "total_bytes": total_bytes,
                    "free_bytes": free_bytes,
                    "percentage": percentage,
                    "breakdown": breakdown,
                },
                None,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to retrieve system quota", extra={"context": {"error": str(exc)}})
            return None, exc

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _ensure_storage_directories(self) -> None:
        """Guarantee that expected storage directories exist."""
        for subdir in ("videos", "frames", "audio", "evidence", "reports", "persons"):
            path = self.storage_base_path / subdir
            path.mkdir(parents=True, exist_ok=True)

    def _build_video_directory(self, date: datetime) -> Path:
        return (
            self.storage_base_path
            / "videos"
            / date.strftime("%Y")
            / date.strftime("%m")
            / date.strftime("%d")
        )

    def _write_file_stream(self, file_obj: FileStorage, destination: Path) -> Tuple[str, int]:
        """Persist streaming file data to disk while calculating checksum."""
        file_obj.stream.seek(0)
        checksum = hashlib.sha256()
        bytes_written = 0

        with open(destination, "wb") as output:
            while True:
                chunk = file_obj.stream.read(8192)
                if not chunk:
                    break
                output.write(chunk)
                checksum.update(chunk)
                bytes_written += len(chunk)

        file_obj.stream.seek(0)
        return checksum.hexdigest(), bytes_written

    def _write_binary(self, destination: Path, data: bytes) -> str:
        checksum = hashlib.sha256(data).hexdigest()
        with open(destination, "wb") as output:
            output.write(data)
        return checksum

    def _get_record(self, file_id: str, file_type: str) -> Optional[Any]:
        if file_type == "video":
            return Video.query.filter_by(id=file_id).first()
        if file_type == "evidence":
            return Evidence.query.filter_by(id=file_id).first()
        raise StorageError(f"Unsupported file type: {file_type}")

    def _check_dependencies(self, record: Any, file_type: str) -> Optional[Exception]:
        if file_type == "video":
            ticket = Ticket.query.filter(
                Ticket.video_id == record.id,
                Ticket.status != "closed",
            ).first()
            if ticket is not None:
                return StorageError("Cannot delete video linked to open tickets")
        if file_type == "evidence":
            ticket = record.ticket
            if ticket and ticket.status != "closed":
                return StorageError("Cannot delete evidence linked to open tickets")
        return None

    def _safe_remove_path(self, path: Optional[Path | str]) -> None:
        if not path:
            return
        try:
            os.remove(path)
        except BuiltinFileNotFoundError:
            logger.debug("File already removed", extra={"context": {"path": str(path)}})
        except PermissionError as exc:
            logger.warning(
                "Permission error while deleting file",
                extra={"context": {"path": str(path), "error": str(exc)}},
            )
        except OSError as exc:
            logger.warning(
                "Unexpected error while deleting file",
                extra={"context": {"path": str(path), "error": str(exc)}},
            )

    def _update_user_quota(self, user_id: str, delta: int) -> None:
        if not user_id or delta == 0:
            return
        cache_key = f"quota:user:{user_id}"
        self.redis_client.hincrby(cache_key, "used_bytes", delta)
        self.redis_client.hset(cache_key, "updated_at", datetime.utcnow().isoformat())

    def _increment_system_usage(self, delta: int) -> None:
        if delta == 0:
            return
        self.redis_client.incrby("quota:system:used_bytes", delta)
        self.redis_client.hset(
            "quota:system:meta",
            mapping={"updated_at": datetime.utcnow().isoformat()},
        )

    def _get_system_usage(self) -> int:
        value = self.redis_client.get("quota:system:used_bytes")
        if value is None:
            total = self._calculate_system_usage_from_db()
            self.redis_client.set("quota:system:used_bytes", total)
            return total
        if isinstance(value, bytes):
            return int(value.decode("utf-8"))
        return int(value)

    def _calculate_user_quota_from_db(self, user_id: str) -> int:
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Video.filesize), 0))
            .filter(Video.user_id == user_id, Video.is_deleted.is_(False))
            .scalar()
        )
        return int(total or 0)

    def _calculate_system_usage_from_db(self) -> int:
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Video.filesize), 0))
            .filter(Video.is_deleted.is_(False))
            .scalar()
        )
        return int(total or 0)

    def _calculate_storage_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = {}
        for subdir in ("videos", "frames", "audio", "evidence"):
            path = self.storage_base_path / subdir
            breakdown[subdir] = self._directory_size(path)
        return breakdown

    def _directory_size(self, path: Path) -> int:
        total_size = 0
        if not path.exists():
            return total_size
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    continue
        return total_size

    def _create_audit_log(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditLog]:
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=self._get_request_ip(),
                user_agent=self._get_request_user_agent(),
                details=details,
            )
            db.session.add(audit_log)
            db.session.flush()
            return audit_log
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.warning(
                "Failed to create audit log",
                extra={"context": {"action": action, "error": str(exc)}},
            )
        return None

    def _get_request_ip(self) -> Optional[str]:
        if not has_request_context():
            return None
        return request.remote_addr

    def _get_request_user_agent(self) -> Optional[str]:
        if not has_request_context():
            return None
        user_agent = request.headers.get("User-Agent")
        return user_agent[:500] if user_agent else None

    def _get_request_user_id(self) -> Optional[str]:
        if not has_request_context():
            return None
        current_user = getattr(g, "current_user", None)
        return getattr(current_user, "id", None)

    @staticmethod
    def _decode_redis_value(value: Any) -> str:
        if value is None:
            return "0"
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)


