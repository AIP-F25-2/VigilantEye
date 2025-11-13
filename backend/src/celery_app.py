from __future__ import annotations

from celery import Celery

from src.config import get_config


def create_celery_app(config_name: str | None = None) -> Celery:
    config = get_config(config_name)

    celery_app = Celery(
        "vigilanteye",
        broker=config.CELERY_BROKER_URL,
        backend=config.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer=config.CELERY_TASK_SERIALIZER,
        accept_content=config.CELERY_ACCEPT_CONTENT,
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        task_soft_time_limit=3000,
    )

    celery_app.conf.task_routes = {
        "src.tasks.analyze_video_task.*": {"queue": "video"},
        "src.tasks.extract_frames_task.*": {"queue": "video"},
        "src.tasks.run_ai_models_task.*": {"queue": "ai"},
        "src.tasks.handle_suspicious_result_task.*": {"queue": "alerts"},
        "src.tasks.cleanup_task.*": {"queue": "maintenance"},
    }

    if config.ENABLE_BEAT:
        celery_app.conf.beat_schedule = {
            "cleanup-expired-files": {
                "task": "src.tasks.cleanup_task.cleanup_expired_files",
                "schedule": 900.0,
            },
            "auto-close-tickets": {
                "task": "src.tasks.cleanup_task.auto_close_tickets",
                "schedule": 600.0,
            },
            "check-ticket-escalations": {
                "task": "src.tasks.cleanup_task.check_ticket_escalations",
                "schedule": 300.0,  # Every 5 minutes
            },
        }
    else:
        celery_app.conf.beat_schedule = {}

    return celery_app


__all__ = ["create_celery_app"]

