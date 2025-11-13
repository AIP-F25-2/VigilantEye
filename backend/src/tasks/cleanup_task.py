from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import redis

from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError

from src.app import db
from src.celery_app import create_celery_app
from src.config import get_config
from src.models.audit_log import AuditLog
from src.models.person import Person
from src.models.ticket import Ticket
from src.models.ticket_history import TicketHistory
from src.models.video import Video
from src.utils.chromadb_manager import ChromaDBManager

config = get_config()
celery_app = create_celery_app()
logger = get_task_logger(__name__)
storage_logger = logging.getLogger(__name__)

redis_client = redis.from_url(config.REDIS_URL)
storage_base_path = Path(config.STORAGE_BASE_PATH).resolve()
cleanup_batch_size = config.CLEANUP_BATCH_SIZE


@celery_app.task(name="src.tasks.cleanup_task.cleanup_expired_files")
def cleanup_expired_files() -> Dict[str, object]:
    """Remove expired videos and persons, reclaiming storage."""
    if not config.CLEANUP_ENABLED:
        logger.info("Cleanup task skipped (disabled via configuration)")
        return {"deleted_videos": 0, "deleted_persons": 0, "freed_bytes": 0, "errors": []}

    metrics = {
        "deleted_videos": 0,
        "deleted_persons": 0,
        "freed_bytes": 0,
        "deleted_face_embeddings": 0,
        "deleted_body_embeddings": 0,
        "errors": [],
    }

    try:
        metrics.update(_cleanup_videos())
        metrics.update(_cleanup_persons(metrics))

        chromadb_manager = ChromaDBManager(config=config)
        chroma_metrics, chroma_error = chromadb_manager.cleanup_expired_embeddings()
        if chroma_error:
            logger.warning(
                "ChromaDB cleanup failed",
                extra={"context": {"error": str(chroma_error)}},
            )
            metrics["errors"].append(str(chroma_error))

        metrics["deleted_face_embeddings"] = chroma_metrics.get("deleted_faces", 0)
        metrics["deleted_body_embeddings"] = chroma_metrics.get("deleted_bodies", 0)

        _create_audit_log(
            action="cleanup_executed",
            details={
                "deleted_videos": metrics["deleted_videos"],
                "deleted_persons": metrics["deleted_persons"],
                "deleted_face_embeddings": metrics["deleted_face_embeddings"],
                "deleted_body_embeddings": metrics["deleted_body_embeddings"],
                "freed_bytes": metrics["freed_bytes"],
                "errors": metrics["errors"],
            },
        )

        logger.info(
            "Cleanup completed",
            extra={
                "context": {
                    "deleted_videos": metrics["deleted_videos"],
                    "deleted_persons": metrics["deleted_persons"],
                    "deleted_face_embeddings": metrics["deleted_face_embeddings"],
                    "deleted_body_embeddings": metrics["deleted_body_embeddings"],
                    "freed_bytes": metrics["freed_bytes"],
                    "errors": metrics["errors"],
                }
            },
        )
    except Exception as exc:  # pragma: no cover
        metrics["errors"].append(str(exc))
        logger.exception("Cleanup task failed", extra={"context": {"error": str(exc)}})

    return metrics


def _cleanup_videos() -> Dict[str, object]:
    deleted_videos = 0
    freed_bytes = 0
    errors: List[str] = []
    commit_counter = 0

    while True:
        expired_videos = (
            Video.query.filter(
                Video.expires_at.isnot(None),
                Video.expires_at < datetime.utcnow(),
                Video.is_deleted.is_(False),
            )
            .order_by(Video.expires_at)
            .limit(cleanup_batch_size)
            .all()
        )

        if not expired_videos:
            break

        for video in expired_videos:
            filepath = video.get_storage_path()
            filesize = video.filesize or 0

            if _delete_file_safe(filepath):
                freed_bytes += filesize
            else:
                errors.append(f"Failed to delete file for video {video.id}")

            _delete_transient_artifacts(video.id)

            video.soft_delete()
            commit_counter += 1
            deleted_videos += 1

            if video.user_id and filesize:
                redis_client.hincrby(f"quota:user:{video.user_id}", "used_bytes", -filesize)
                redis_client.hset(
                    f"quota:user:{video.user_id}", "updated_at", datetime.utcnow().isoformat()
                )
                redis_client.incrby("quota:system:used_bytes", -filesize)

            if commit_counter % 100 == 0:
                _batch_commit(db.session)

        _batch_commit(db.session)

    return {
        "deleted_videos": deleted_videos,
        "freed_bytes": freed_bytes,
        "errors": errors,
    }


def _cleanup_persons(metrics: Dict[str, object]) -> Dict[str, object]:
    deleted_persons = 0
    errors: List[str] = metrics.get("errors", [])  # type: ignore[assignment]
    commit_counter = 0

    chromadb_manager = ChromaDBManager(config=config)

    while True:
        expired_persons = (
            Person.query.filter(
                Person.expires_at.isnot(None),
                Person.expires_at < datetime.utcnow(),
                Person.is_deleted.is_(False),
            )
            .order_by(Person.expires_at)
            .limit(cleanup_batch_size)
            .all()
        )

        if not expired_persons:
            break

        for person in expired_persons:
            person.soft_delete()
            commit_counter += 1
            deleted_persons += 1

            success, chroma_error = chromadb_manager.delete_person_embeddings(person.person_tracking_id)
            if chroma_error:
                errors.append(
                    f"Failed to delete embeddings for person {person.person_tracking_id}: {chroma_error}"
                )
            elif not success:
                errors.append(
                    f"Embeddings deletion status unknown for person {person.person_tracking_id}"
                )

            if commit_counter % 100 == 0:
                _batch_commit(db.session)

        _batch_commit(db.session)

    return {
        "deleted_persons": deleted_persons,
        "errors": errors,
    }


@celery_app.task(name="src.tasks.cleanup_task.auto_close_tickets")
def auto_close_tickets() -> Dict[str, object]:
    if not config.CLEANUP_ENABLED:
        logger.info("Auto-close skipped (cleanup disabled)")
        return {"closed_tickets": 0, "errors": []}

    closed_tickets = 0
    errors: List[str] = []
    commit_counter = 0

    try:
        while True:
            candidates = (
                Ticket.query.filter(
                    Ticket.auto_close_at.isnot(None),
                    Ticket.auto_close_at < datetime.utcnow(),
                    Ticket.status != "closed",
                )
                .order_by(Ticket.auto_close_at)
                .limit(cleanup_batch_size)
                .all()
            )

            if not candidates:
                break

            for ticket in candidates:
                ticket.status = "closed"
                ticket.closed_at = datetime.utcnow()
                history = TicketHistory(
                    ticket_id=ticket.id,
                    event="auto_closed",
                    details="Automatically closed after timeout",
                )
                db.session.add(history)
                commit_counter += 1
                closed_tickets += 1

                if commit_counter % 100 == 0:
                    _batch_commit(db.session)

            _batch_commit(db.session)

        _create_audit_log(
            action="tickets_auto_closed",
            details={"count": closed_tickets},
        )

        logger.info(
            "Auto-close tickets completed",
            extra={"context": {"closed_tickets": closed_tickets}},
        )
    except Exception as exc:  # pragma: no cover
        errors.append(str(exc))
        logger.exception("Auto-close tickets task failed", extra={"context": {"error": str(exc)}})

    return {"closed_tickets": closed_tickets, "errors": errors}


@celery_app.task(name="src.tasks.cleanup_task.check_ticket_escalations")
def check_ticket_escalations() -> Dict[str, object]:
    """Check for tickets needing escalation and escalate them."""
    if not config.CLEANUP_ENABLED:
        logger.info("Auto-escalation skipped (cleanup disabled)")
        return {"escalated_tickets": 0, "errors": []}

    escalated_tickets = 0
    errors: List[str] = []
    commit_counter = 0

    try:
        # Calculate escalation threshold
        escalation_threshold = datetime.utcnow() - timedelta(
            minutes=config.TICKET_ESCALATION_TIMEOUT_MINUTES
        )

        # Query tickets needing escalation
        from src.config.constants import TicketStatus

        while True:
            tickets = (
                Ticket.query.filter(
                    Ticket.status == TicketStatus.OPEN,
                    Ticket.acknowledged_at.is_(None),
                    Ticket.created_at < escalation_threshold,
                    Ticket.escalated.is_(False),
                )
                .order_by(Ticket.created_at)
                .limit(cleanup_batch_size)
                .all()
            )

            if not tickets:
                break

            for ticket in tickets:
                # Call ticket.check_sla_breach() to set sla_breach flag
                ticket.check_sla_breach()

                # Call ticket.escalate() to increment escalation_count and set escalation_sent_at
                ticket.escalate()

                # Create TicketHistory entry
                history = TicketHistory(
                    ticket_id=ticket.id,
                    event="auto_escalated",
                    details="Not acknowledged within 15 minutes",
                )
                db.session.add(history)

                # Send escalation alert via messenger service (stub for now)
                try:
                    # MessengerService will be implemented in Phase 10
                    # For now, just log
                    logger.info(
                        f"Escalation alert for ticket {ticket.id} (MessengerService not yet implemented)"
                    )
                except Exception as exc:
                    errors.append(f"Failed to send escalation for ticket {ticket.id}: {exc}")

                commit_counter += 1
                escalated_tickets += 1

                # Commit in batches of 100
                if commit_counter % 100 == 0:
                    _batch_commit(db.session)

            _batch_commit(db.session)

        _create_audit_log(
            action="tickets_auto_escalated",
            details={"count": escalated_tickets, "errors": errors},
        )

        logger.info(
            "Auto-escalation completed",
            extra={"context": {"escalated_tickets": escalated_tickets, "errors": errors}},
        )
    except Exception as exc:  # pragma: no cover
        errors.append(str(exc))
        logger.exception("Auto-escalation task failed", extra={"context": {"error": str(exc)}})

    return {"escalated_tickets": escalated_tickets, "errors": errors}


@celery_app.task(name="src.tasks.cleanup_task.sync_quota_to_database")
def sync_quota_to_database() -> Dict[str, object]:
    """Persist cached quota values for analytics purposes."""
    results: Dict[str, int] = {}
    errors: List[str] = []

    try:
        keys = redis_client.keys("quota:user:*")
        for key in keys:
            user_id = key.decode("utf-8").split(":")[-1] if isinstance(key, bytes) else str(key).split(":")[-1]
            used_bytes = redis_client.hget(key, "used_bytes")
            if isinstance(used_bytes, bytes):
                used_value = int(used_bytes.decode("utf-8"))
            elif used_bytes is None:
                used_value = 0
            else:
                used_value = int(used_bytes)
            results[user_id] = used_value

        storage_logger.debug(
            "Quota sync snapshot",
            extra={"context": {"entries": len(results)}},
        )
    except Exception as exc:  # pragma: no cover
        errors.append(str(exc))
        logger.exception("Quota sync failed", extra={"context": {"error": str(exc)}})

    return {"synced_users": len(results), "errors": errors}


def _delete_file_safe(filepath: str) -> bool:
    try:
        os.remove(filepath)
        return True
    except FileNotFoundError:
        storage_logger.debug("File already deleted", extra={"context": {"path": filepath}})
        return False
    except PermissionError as exc:
        storage_logger.warning(
            "Permission error while deleting file",
            extra={"context": {"path": filepath, "error": str(exc)}},
        )
    except OSError as exc:
        storage_logger.warning(
            "Unexpected error while deleting file",
            extra={"context": {"path": filepath, "error": str(exc)}},
        )
    return False


def _delete_transient_artifacts(video_id: str) -> None:
    temp_dirs = [
        storage_base_path / "frames" / video_id,
        storage_base_path / "audio" / video_id,
    ]
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            for item in temp_dir.glob("*"):
                if item.is_file():
                    _delete_file_safe(str(item))
            try:
                temp_dir.rmdir()
            except OSError:
                continue


def _batch_commit(session, batch_size: int = 100) -> None:
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        storage_logger.exception("Batch commit failed", extra={"context": {"error": str(exc)}})


def _create_audit_log(action: str, details: Optional[Dict[str, object]] = None) -> None:
    try:
        audit_log = AuditLog(
            user_id=None,
            action=action,
            resource_type="maintenance",
            resource_id=None,
            details=details,
        )
        db.session.add(audit_log)
        db.session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover
        db.session.rollback()
        storage_logger.warning(
            "Failed to create audit log",
            extra={"context": {"action": action, "error": str(exc)}},
        )


