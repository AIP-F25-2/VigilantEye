import logging
import os
from pathlib import Path
from typing import Dict, Type
from urllib.parse import quote_plus

from src.config.constants import SUPPORTED_VIDEO_FORMATS as DEFAULT_SUPPORTED_VIDEO_FORMATS

logger = logging.getLogger(__name__)

def _get_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_list(value: str | None, default: list[str] | None = None) -> list[str]:
    if value is None or value.strip() == "":
        return default[:] if default else []
    return [item.strip() for item in value.split(",") if item.strip()]


class BaseConfig:
    """Base configuration shared across environments."""

    VALIDATION_STRICT = True

    # Application
    APP_NAME = os.getenv("APP_NAME", "VigilantEye")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    DEBUG = _get_bool(os.getenv("DEBUG"), default=False)
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

    # Database
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "vigilanteye")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = int(os.getenv("SQLALCHEMY_POOL_SIZE", "10"))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "20"))

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # ChromaDB
    CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
    CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
    CHROMADB_COLLECTION_NAME = os.getenv(
        "CHROMADB_COLLECTION_NAME", "vigilanteye_vectors"
    )

    # Celery
    ENABLE_BEAT = _get_bool(os.getenv("ENABLE_BEAT"), default=False)
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]

    # Storage
    STORAGE_BASE_PATH = os.getenv("STORAGE_BASE_PATH", "./storage")
    VIDEO_TTL_HOURS = int(os.getenv("VIDEO_TTL_HOURS", "2"))
    PERSON_VECTOR_TTL_HOURS = int(os.getenv("PERSON_VECTOR_TTL_HOURS", "2"))
    TICKET_AUTO_CLOSE_HOURS = int(os.getenv("TICKET_AUTO_CLOSE_HOURS", "2"))
    MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))
    SUPPORTED_VIDEO_FORMATS = _get_list(
        os.getenv("SUPPORTED_VIDEO_FORMATS"),
        DEFAULT_SUPPORTED_VIDEO_FORMATS,
    )

    # Storage Quota
    USER_QUOTA_MAX_GB = int(os.getenv("USER_QUOTA_MAX_GB", "10"))
    SYSTEM_QUOTA_WARNING_PERCENTAGE = int(
        os.getenv("SYSTEM_QUOTA_WARNING_PERCENTAGE", "80")
    )

    # Cleanup Configuration
    CLEANUP_BATCH_SIZE = int(os.getenv("CLEANUP_BATCH_SIZE", "1000"))
    CLEANUP_ENABLED = _get_bool(os.getenv("CLEANUP_ENABLED"), default=True)

    # Video Processing
    FRAME_EXTRACTION_INTERVAL = float(
        os.getenv("FRAME_EXTRACTION_INTERVAL", "1.0")
    )
    MAX_CONCURRENT_STREAMS = int(os.getenv("MAX_CONCURRENT_STREAMS", "4"))
    MOTION_DETECTION_THRESHOLD = float(
        os.getenv("MOTION_DETECTION_THRESHOLD", "0.3")
    )

    # AI Models
    MODELS_CACHE_PATH = os.getenv("MODELS_CACHE_PATH", "./models_cache")
    AI_CONFIDENCE_THRESHOLD = float(
        os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7")
    )
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    TELEGRAM_ESCALATION_CHANNEL = os.getenv("TELEGRAM_ESCALATION_CHANNEL", "")
    TELEGRAM_RETRY_ATTEMPTS = int(os.getenv("TELEGRAM_RETRY_ATTEMPTS", "3"))
    TELEGRAM_RETRY_DELAY = int(os.getenv("TELEGRAM_RETRY_DELAY", "2"))

    # Ticket Management
    TICKET_ESCALATION_TIMEOUT_MINUTES = int(
        os.getenv("TICKET_ESCALATION_TIMEOUT_MINUTES", "15")
    )

    # Security
    JWT_ACCESS_TOKEN_EXPIRES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")
    )
    JWT_REFRESH_TOKEN_EXPIRES = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000")
    )
    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5 per 15 minutes")
    ENFORCE_ACCESS_TOKEN_ALLOWLIST = _get_bool(
        os.getenv("ENFORCE_ACCESS_TOKEN_ALLOWLIST"), default=False
    )

    # CORS
    CORS_ORIGINS = _get_list(
        os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ),
        ["http://localhost:5173", "http://localhost:3000"],
    )

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_MAX_BYTES = int(os.getenv("LOG_FILE_MAX_BYTES", "104857600"))
    LOG_FILE_BACKUP_COUNT = int(os.getenv("LOG_FILE_BACKUP_COUNT", "10"))

    def __init__(self) -> None:
        self._run_validations(strict=self.VALIDATION_STRICT)

    def _run_validations(self, strict: bool) -> None:
        validators = [
            self.validate_required_settings,
            self.validate_database_connection,
            self.validate_redis_connection,
        ]
        for validator in validators:
            try:
                validator()
            except ValueError as exc:
                if strict:
                    raise
                logger.warning(
                    "Configuration warning (%s.%s): %s",
                    self.__class__.__name__,
                    validator.__name__,
                    exc,
                )
        self.validate_storage_paths()

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD) if self.MYSQL_PASSWORD else None
        auth_part = f"{user}:{password}@" if password is not None else f"{user}@"
        return (
            f"mysql+pymysql://{auth_part}{self.MYSQL_HOST}:{self.MYSQL_PORT}/"
            f"{self.MYSQL_DATABASE}"
        )

    @property
    def REDIS_URL(self) -> str:
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def validate_required_settings(self) -> None:
        required = {
            "SECRET_KEY": self.SECRET_KEY,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
            "MYSQL_HOST": self.MYSQL_HOST,
            "MYSQL_USER": self.MYSQL_USER,
            "MYSQL_DATABASE": self.MYSQL_DATABASE,
            "CELERY_BROKER_URL": self.CELERY_BROKER_URL,
            "CELERY_RESULT_BACKEND": self.CELERY_RESULT_BACKEND,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required configuration values: {', '.join(missing)}"
            )

    def validate_database_connection(self) -> None:
        if not isinstance(self.MYSQL_PORT, int) or self.MYSQL_PORT <= 0:
            raise ValueError("MYSQL_PORT must be a positive integer")
        if not self.MYSQL_PASSWORD:
            raise ValueError("MYSQL_PASSWORD must be set for secure operation")

    def validate_redis_connection(self) -> None:
        if not isinstance(self.REDIS_PORT, int) or self.REDIS_PORT <= 0:
            raise ValueError("REDIS_PORT must be a positive integer")

    def validate_storage_paths(self) -> None:
        base_path = Path(self.STORAGE_BASE_PATH)
        base_path.mkdir(parents=True, exist_ok=True)

        models_cache = Path(self.MODELS_CACHE_PATH)
        models_cache.mkdir(parents=True, exist_ok=True)

    @property
    def USER_QUOTA_MAX_BYTES(self) -> int:
        return self.USER_QUOTA_MAX_GB * 1024 * 1024 * 1024


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    VALIDATION_STRICT = False


class StagingConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = "INFO"


class ProductionConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = "WARNING"
    CORS_ORIGINS = _get_list(os.getenv("CORS_ORIGINS", ""), [])


CONFIG_MAP: Dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> BaseConfig:
    """Return the configuration instance for the given environment."""
    env_name = config_name or os.getenv("FLASK_ENV", "development").lower()
    config_class = CONFIG_MAP.get(env_name, DevelopmentConfig)
    return config_class()

