"""AI Services Configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseSettings):
    """AI Services configuration."""

    # OpenAI API
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")
    
    # Telegram Integration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = Field(default="", alias="TELEGRAM_WEBHOOK_SECRET")
    telegram_escalation_channel: str = Field(default="", alias="TELEGRAM_ESCALATION_CHANNEL")
    
    # Whisper (Speech-to-Text)
    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")  # tiny, base, small, medium, large
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")  # cpu or cuda
    
    # Audio Classification
    audio_classification_threshold: float = Field(default=0.3, alias="AUDIO_CLASSIFICATION_THRESHOLD")
    
    # Face Detection
    face_detection_confidence: float = Field(default=0.9, alias="FACE_DETECTION_CONFIDENCE")
    face_recognition_threshold: float = Field(default=0.6, alias="FACE_RECOGNITION_THRESHOLD")
    
    # Object Detection
    object_detection_model: str = Field(default="yolov8n.pt", alias="OBJECT_DETECTION_MODEL")
    object_detection_confidence: float = Field(default=0.5, alias="OBJECT_DETECTION_CONFIDENCE")
    
    # OCR
    ocr_languages: str = Field(default="en", alias="OCR_LANGUAGES")  # Comma-separated
    
    # Vector Database
    vector_db_type: str = Field(default="chromadb", alias="VECTOR_DB_TYPE")  # chromadb or faiss
    vector_db_path: str = Field(default="storage/vector_db", alias="VECTOR_DB_PATH")
    vector_dimension: int = Field(default=512, alias="VECTOR_DIMENSION")
    
    # Threat Detection
    threat_detection_model: str = Field(default="gpt-4-turbo-preview", alias="THREAT_DETECTION_MODEL")
    threat_threshold: float = Field(default=0.7, alias="THREAT_THRESHOLD")
    
    # Evidence Storage
    evidence_storage_path: str = Field(default="storage/evidence", alias="EVIDENCE_STORAGE_PATH")
    
    # Processing
    ai_batch_size: int = Field(default=4, alias="AI_BATCH_SIZE")
    ai_max_workers: int = Field(default=4, alias="AI_MAX_WORKERS")
    
    # Device
    ai_device: str = Field(default="cpu", alias="AI_DEVICE")  # cpu, cuda, mps
    
    # Model Cache
    model_cache_path: str = Field(default="storage/model_cache", alias="MODEL_CACHE_PATH")
    model_cache_enabled: bool = Field(default=True, alias="MODEL_CACHE_ENABLED")
    model_cache_max_size_gb: float = Field(default=10.0, alias="MODEL_CACHE_MAX_SIZE_GB")
    
    # Periodic Cleanup
    cleanup_enabled: bool = Field(default=True, alias="CLEANUP_ENABLED")
    cleanup_interval_hours: int = Field(default=24, alias="CLEANUP_INTERVAL_HOURS")
    person_data_retention_days: int = Field(default=30, alias="PERSON_DATA_RETENTION_DAYS")
    embedding_data_retention_days: int = Field(default=90, alias="EMBEDDING_DATA_RETENTION_DAYS")
    media_retention_days: int = Field(default=60, alias="MEDIA_RETENTION_DAYS")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
