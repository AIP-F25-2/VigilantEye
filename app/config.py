from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    STORAGE_PATH: Path = Path("./storage")
    IMAGE_PERIOD_SEC: int = Field(1, env="IMAGE_PERIOD_SEC")
    TTL_SECONDS: int = Field(60 * 60 * 2, env="TTL_SECONDS")
    JWT_SECRET: str = Field("changeme", env="JWT_SECRET")
    TELEGRAM_BOT_TOKEN: str | None = Field(None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str | None = Field(None, env="TELEGRAM_CHAT_ID")
    AUTO_CLOSE_TICKET_SECONDS: int = Field(60 * 60 * 2, env="AUTO_CLOSE_TICKET_SECONDS")
    THREAD_POOL_WORKERS: int = Field(4, env="THREAD_POOL_WORKERS")
    DATABASE_URL: str = Field("sqlite:///./surveillance.db", env="DATABASE_URL")

    class Config:
        env_file = ".env"

settings = Settings()
