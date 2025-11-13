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
    # Video Processing - Additional Settings
    THUMBNAIL_WIDTH = int(os.getenv("THUMBNAIL_WIDTH", "320"))
    THUMBNAIL_HEIGHT = int(os.getenv("THUMBNAIL_HEIGHT", "240"))
    MAX_RESOLUTION_WIDTH = int(os.getenv("MAX_RESOLUTION_WIDTH", "3840"))  # 4K
    MAX_RESOLUTION_HEIGHT = int(os.getenv("MAX_RESOLUTION_HEIGHT", "2160"))  # 4K
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")  # Path to FFmpeg binary
    FRAME_BUFFER_SIZE = int(os.getenv("FRAME_BUFFER_SIZE", "100"))  # Max frames in buffer per stream

    # AI Models
    MODELS_CACHE_PATH = os.getenv("MODELS_CACHE_PATH", "./models_cache")
    AI_CONFIDENCE_THRESHOLD = float(
        os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7")
    )
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    # LLM Analyzer Configuration
    LLM_CONFIDENCE_THRESHOLD = float(os.getenv('LLM_CONFIDENCE_THRESHOLD', '0.7'))  # Min confidence to flag as suspicious
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '500'))  # Max tokens in LLM response
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))  # Lower = more deterministic (0.0-1.0)
    LLM_TIMEOUT_SECONDS = int(os.getenv('LLM_TIMEOUT_SECONDS', '30'))  # Max time for LLM inference
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '2'))  # Retries if JSON parsing fails
    USE_CHAIN_OF_THOUGHT = _get_bool(os.getenv('USE_CHAIN_OF_THOUGHT'), default=True)  # Enable CoT reasoning
    USE_FEW_SHOT_EXAMPLES = _get_bool(os.getenv('USE_FEW_SHOT_EXAMPLES'), default=True)  # Include examples in prompt
    ENABLE_RULE_BASED_FALLBACK = _get_bool(os.getenv('ENABLE_RULE_BASED_FALLBACK'), default=True)  # Fallback if LLM fails

    # Person Detection Configuration
    PERSON_DETECTION_CONFIDENCE = float(os.getenv("PERSON_DETECTION_CONFIDENCE", "0.5"))
    FACE_DETECTION_CONFIDENCE = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.9"))
    REID_SIMILARITY_THRESHOLD = float(os.getenv("REID_SIMILARITY_THRESHOLD", "0.8"))
    MAX_PERSONS_PER_FRAME = int(os.getenv("MAX_PERSONS_PER_FRAME", "50"))
    PERSON_MIN_SIZE = int(os.getenv("PERSON_MIN_SIZE", "50"))
    SAVE_PERSON_THUMBNAILS = _get_bool(os.getenv("SAVE_PERSON_THUMBNAILS"), default=True)

    # Scene Analysis Configuration
    SCENE_CONFIDENCE_THRESHOLD = float(os.getenv("SCENE_CONFIDENCE_THRESHOLD", "0.7"))
    BLIP2_MODEL_NAME = os.getenv("BLIP2_MODEL_NAME", "Salesforce/blip2-opt-2.7b")
    BLIP2_MAX_LENGTH = int(os.getenv("BLIP2_MAX_LENGTH", "100"))
    BLIP2_PROMPT = os.getenv(
        "BLIP2_PROMPT",
        "Describe the scene in one sentence highlighting environment, lighting, weather, and crowd.",
    )
    USE_SCENE_FALLBACK = _get_bool(os.getenv("USE_SCENE_FALLBACK"), default=True)

    # Object Detection Configuration
    OBJECT_DETECTION_CONFIDENCE = float(os.getenv("OBJECT_DETECTION_CONFIDENCE", "0.5"))
    OBJECT_MIN_SIZE = int(os.getenv("OBJECT_MIN_SIZE", "30"))
    MAX_OBJECTS_PER_FRAME = int(os.getenv("MAX_OBJECTS_PER_FRAME", "100"))
    OBJECT_PERSON_IOU_THRESHOLD = float(os.getenv("OBJECT_PERSON_IOU_THRESHOLD", "0.1"))
    OBJECT_PERSON_MAX_DISTANCE = float(os.getenv("OBJECT_PERSON_MAX_DISTANCE", "100"))
    DETECT_ALL_OBJECTS = _get_bool(os.getenv("DETECT_ALL_OBJECTS"), default=False)

    # Speech-to-Text Configuration
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny|base|small|medium|large
    TRANSCRIPTION_CONFIDENCE_THRESHOLD = float(os.getenv("TRANSCRIPTION_CONFIDENCE_THRESHOLD", "0.7"))
    ENABLE_NOISE_REDUCTION = _get_bool(os.getenv("ENABLE_NOISE_REDUCTION"), default=True)
    ENABLE_SPEAKER_DIARIZATION = _get_bool(os.getenv("ENABLE_SPEAKER_DIARIZATION"), default=True)
    THREAT_KEYWORDS = os.getenv(
        "THREAT_KEYWORDS", "gun,shoot,kill,bomb,help,fire,weapon,attack,knife,threat"
    ).split(",")
    PROFANITY_KEYWORDS = os.getenv("PROFANITY_KEYWORDS", "").split(",")  # Empty by default, configurable

    # Audio Classification Configuration
    AUDIO_CLASSIFICATION_CONFIDENCE = float(os.getenv("AUDIO_CLASSIFICATION_CONFIDENCE", "0.5"))
    MAX_SOUNDS_PER_SEGMENT = int(os.getenv("MAX_SOUNDS_PER_SEGMENT", "5"))
    YAMNET_MODEL_URL = os.getenv("YAMNET_MODEL_URL", "https://tfhub.dev/google/yamnet/1")

    USE_GPU_INFERENCE = _get_bool(os.getenv("USE_GPU_INFERENCE"), default=True)

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    TELEGRAM_ESCALATION_CHANNEL = os.getenv("TELEGRAM_ESCALATION_CHANNEL", "")
    TELEGRAM_PRIMARY_CHANNEL = os.getenv(
        "TELEGRAM_PRIMARY_CHANNEL", os.getenv("TELEGRAM_ESCALATION_CHANNEL", "")
    )
    TELEGRAM_RETRY_ATTEMPTS = int(os.getenv("TELEGRAM_RETRY_ATTEMPTS", "3"))
    TELEGRAM_RETRY_DELAY = int(os.getenv("TELEGRAM_RETRY_DELAY", "2"))
    TELEGRAM_RATE_LIMIT_MAX = int(os.getenv("TELEGRAM_RATE_LIMIT_MAX", "10"))
    TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")

    # Report Generation Configuration
    REPORT_CACHE_TTL_SECONDS = int(os.getenv("REPORT_CACHE_TTL_SECONDS", "3600"))
    REPORT_WATERMARK_TEXT = os.getenv("REPORT_WATERMARK_TEXT", "CONFIDENTIAL")
    REPORT_LOGO_PATH = os.getenv("REPORT_LOGO_PATH", "")
    REPORT_INCLUDE_SIMILAR_PERSONS = _get_bool(os.getenv("REPORT_INCLUDE_SIMILAR_PERSONS"), default=True)
    REPORT_SIMILAR_PERSONS_TIME_WINDOW = int(os.getenv("REPORT_SIMILAR_PERSONS_TIME_WINDOW", "2"))
    REPORT_SIMILAR_PERSONS_TOP_K = int(os.getenv("REPORT_SIMILAR_PERSONS_TOP_K", "5"))
    REPORT_PAGE_SIZE = os.getenv("REPORT_PAGE_SIZE", "letter")
    REPORT_FONT_NAME = os.getenv("REPORT_FONT_NAME", "Helvetica")

    # AI Orchestrator Configuration
    AI_ORCHESTRATOR_ENABLED = _get_bool(os.getenv("AI_ORCHESTRATOR_ENABLED"), default=True)
    AI_ORCHESTRATOR_AUTO_ANALYZE = _get_bool(os.getenv("AI_ORCHESTRATOR_AUTO_ANALYZE"), default=False)
    AI_ORCHESTRATOR_PARALLEL_WORKERS = int(os.getenv("AI_ORCHESTRATOR_PARALLEL_WORKERS", "5"))
    AI_ORCHESTRATOR_TIMEOUT_SECONDS = int(os.getenv("AI_ORCHESTRATOR_TIMEOUT_SECONDS", "300"))
    AI_ORCHESTRATOR_SAVE_TEMP_FILES = _get_bool(os.getenv("AI_ORCHESTRATOR_SAVE_TEMP_FILES"), default=False)
    AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES = _get_bool(os.getenv("AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES"), default=False)

    # WebSocket Configuration
    WEBSOCKET_ENABLED = _get_bool(os.getenv("WEBSOCKET_ENABLED"), default=True)
    WEBSOCKET_ASYNC_MODE = os.getenv("WEBSOCKET_ASYNC_MODE", "threading")
    WEBSOCKET_PING_INTERVAL = int(os.getenv("WEBSOCKET_PING_INTERVAL", "25"))
    WEBSOCKET_PING_TIMEOUT = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "60"))

    # Health & Metrics Configuration
    HEALTH_CHECK_CACHE_SECONDS = int(os.getenv("HEALTH_CHECK_CACHE_SECONDS", "10"))  # Cache expensive checks
    METRICS_HISTORY_HOURS = int(os.getenv("METRICS_HISTORY_HOURS", "24"))  # AI metrics lookback period
    LATENCY_TRACKER_MAX_SAMPLES = int(os.getenv("LATENCY_TRACKER_MAX_SAMPLES", "1000"))  # Max latencies per endpoint
    STORAGE_WARNING_THRESHOLD = int(os.getenv("STORAGE_WARNING_THRESHOLD", "80"))  # Storage usage warning %

    def validate_telegram_config(self) -> None:
        """Validate Telegram configuration and warn about potential real tokens in debug mode."""
        if self.TELEGRAM_BOT_TOKEN and self.DEBUG:
            if ':' in self.TELEGRAM_BOT_TOKEN and len(self.TELEGRAM_BOT_TOKEN) > 30:
                logger.warning(
                    "Potential real Telegram token detected in config - consider using placeholders"
                )

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
            self.validate_telegram_config,
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

