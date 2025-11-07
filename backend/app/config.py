import os
from datetime import timedelta

import torch


class Config:
    """Base configuration for the VigilentEye backend."""

    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.getenv("FLASK_ENV") == "development"
    TESTING = False

    # JWT configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # MySQL configuration
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DB = os.getenv("MYSQL_DB", "vigilenteye")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20

    # Azure Cosmos DB configuration
    COSMOS_DB_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
    COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
    COSMOS_DB_DATABASE = "vigilenteye"
    COSMOS_DB_PERSON_CONTAINER = "person_vectors"
    COSMOS_DB_IMAGE_CONTAINER = "image_vectors"

    # Telegram configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "supersecret")
    TELEGRAM_ESCALATION_CHANNEL = os.getenv("TELEGRAM_ESCALATION_CHANNEL")
    TELEGRAM_SECONDARY_CHANNEL = os.getenv("TELEGRAM_SECONDARY_CHANNEL")

    # Storage configuration
    STORAGE_BASE_PATH = os.getenv("STORAGE_PATH", "./storage")
    VIDEO_STORAGE_PATH = os.path.join(STORAGE_BASE_PATH, "videos")
    EVIDENCE_STORAGE_PATH = os.path.join(STORAGE_BASE_PATH, "evidence")
    MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "./models")
    VIDEO_TTL_HOURS = int(os.getenv("VIDEO_TTL_HOURS", 2))
    PERSON_VECTOR_TTL_HOURS = int(os.getenv("PERSON_VECTOR_TTL_HOURS", 2))
    MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", 500))
    MAX_CONTENT_LENGTH = MAX_VIDEO_SIZE_MB * 1024 * 1024

    # Video processing configuration
    FRAME_EXTRACTION_PERIOD = float(os.getenv("FRAME_PERIOD", 1.0))
    SUPPORTED_VIDEO_FORMATS = ["mp4", "avi", "mov", "webm", "mkv"]
    VIDEO_FRAME_WIDTH = 1280
    VIDEO_FRAME_HEIGHT = 720

    # Ticket management configuration
    TICKET_AUTO_CLOSE_HOURS = int(os.getenv("TICKET_AUTO_CLOSE_HOURS", 2))
    TICKET_ESCALATION_MINUTES = int(os.getenv("TICKET_ESCALATION_MINUTES", 15))

    # AI model settings
    AI_FACE_MODEL = os.getenv("AI_FACE_MODEL", "retinaface")
    AI_LLM_MODEL = os.getenv(
        "AI_LLM_MODEL", "microsoft/Phi-3-mini-4k-instruct"
    )
    AI_IMAGE_CAPTION_MODEL = "Salesforce/blip-image-captioning-large"
    AI_OBJECT_DETECTION_MODEL = "yolov8x.pt"
    AI_WHISPER_MODEL = os.getenv("AI_WHISPER_MODEL", "base")
    AI_MAX_WORKERS = int(os.getenv("AI_MAX_WORKERS", 3))
    AI_DEVICE = os.getenv("AI_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/vigilenteye.log")
    LOG_MAX_BYTES = 10 * 1024 * 1024
    LOG_BACKUP_COUNT = 5

    # CORS configuration
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
    CORS_SUPPORTS_CREDENTIALS = True

    # Rate limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_LOGIN = "5 per minute"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration for production deployments."""
        if os.getenv("FLASK_ENV") == "production":
            missing = []
            for key in ("COSMOS_DB_ENDPOINT", "COSMOS_DB_KEY", "TELEGRAM_BOT_TOKEN"):
                if not getattr(cls, key):
                    missing.append(key)
            if missing:
                raise ValueError(
                    "Missing required configuration values in production: "
                    + ", ".join(missing)
                )

