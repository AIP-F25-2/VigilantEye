import datetime
import json
import logging
import time
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

REQUEST_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar(
    "REQUEST_CONTEXT", default={}
)
SENSITIVE_KEYS = {"password", "token", "secret", "authorization"}


class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, "context", {}) or {}
        sanitized_context = {
            key: ("<redacted>" if self._is_sensitive(key) else value)
            for key, value in context.items()
        }

        log_record = {
            "timestamp": datetime.datetime.utcfromtimestamp(record.created)
            .isoformat(timespec="milliseconds")
            + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": sanitized_context,
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "user_role": getattr(record, "user_role", None),
        }

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)

    @staticmethod
    def _is_sensitive(key: str) -> bool:
        return any(secret_key in key.lower() for secret_key in SENSITIVE_KEYS)


class RequestContextFilter(logging.Filter):
    """Inject request context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        context = REQUEST_CONTEXT.get()
        record.request_id = context.get("request_id")
        record.user_id = context.get("user_id")
        record.user_role = context.get("user_role")
        record.context = context.get("extra", {})
        return True


def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    user_role: str | None = None,
    extra: Dict[str, Any] | None = None,
) -> None:
    REQUEST_CONTEXT.set(
        {
            "request_id": request_id,
            "user_id": user_id,
            "user_role": user_role,
            "extra": extra or {},
        }
    )


def clear_request_context() -> None:
    REQUEST_CONTEXT.set({})


def _create_rotating_file_handler(
    log_dir: Path,
    filename: str,
    max_bytes: int,
    backup_count: int,
    level: int,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        log_dir / filename, maxBytes=max_bytes, backupCount=backup_count
    )
    handler.setLevel(level)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestContextFilter())
    return handler


def _create_console_handler(level: int) -> logging.Handler:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(JSONFormatter())
    console_handler.addFilter(RequestContextFilter())
    return console_handler


def setup_logging(config: Any) -> None:
    """Configure application-wide logging based on the active config."""
    log_level = getattr(logging, str(config.LOG_LEVEL).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logs during reloads
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    error_handler = _create_rotating_file_handler(
        log_dir,
        "errors.log",
        config.LOG_FILE_MAX_BYTES,
        config.LOG_FILE_BACKUP_COUNT,
        logging.ERROR,
    )
    root_logger.addHandler(error_handler)

    if config.DEBUG:
        root_logger.addHandler(_create_console_handler(log_level))

    logger_file_map = {
        "src.api": "api.log",
        "src.tasks": "celery.log",
        "src.ai_modules": "ai_inference.log",
    }

    for logger_name, filename in logger_file_map.items():
        named_logger = logging.getLogger(logger_name)
        named_logger.setLevel(log_level)
        for handler in list(named_logger.handlers):
            named_logger.removeHandler(handler)
        named_logger.addHandler(
            _create_rotating_file_handler(
                log_dir,
                filename,
                config.LOG_FILE_MAX_BYTES,
                config.LOG_FILE_BACKUP_COUNT,
                log_level,
            )
        )
        named_logger.propagate = True


__all__ = [
    "setup_logging",
    "set_request_context",
    "clear_request_context",
    "RequestContextFilter",
]

