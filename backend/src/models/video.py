import os
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.config import get_config
from src.config.constants import AnalysisResult, VideoStatus
from src.models.base import BaseModel, TTLMixin

_config = get_config()
STORAGE_BASE_PATH = _config.STORAGE_BASE_PATH
VIDEO_TTL_HOURS = _config.VIDEO_TTL_HOURS


class Video(TTLMixin, BaseModel):
    __tablename__ = "videos"

    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    camera_id = Column(CHAR(36), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    upload_type = Column(String(20), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filesize = Column(BigInteger, nullable=True)
    duration = Column(Float, nullable=True)
    fps = Column(Integer, nullable=True)
    resolution = Column(String(20), nullable=True)
    checksum = Column(String(64), nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=(
            VideoStatus.UPLOADING.value
            if hasattr(VideoStatus.UPLOADING, "value")
            else str(VideoStatus.UPLOADING)
        ),
    )
    analysis_result = Column(String(20), nullable=True)
    analysis_completed_at = Column(DateTime, nullable=True)

    uploader = relationship("User", back_populates="videos")
    camera = relationship("Camera", back_populates="videos")
    evidence = relationship(
        "Evidence",
        back_populates="video",
        passive_deletes=True,
    )
    persons = relationship(
        "Person",
        back_populates="video",
        passive_deletes=True,
    )
    tickets = relationship("Ticket", back_populates="video")

    __table_args__ = (
        CheckConstraint(
            "upload_type IN ('upload', 'stream')",
            name="ck_videos_upload_type_valid",
        ),
        CheckConstraint(
            "status IN ('uploading', 'processing', 'ready', 'analyzing', 'analyzed', 'error')",
            name="ck_videos_status_valid",
        ),
        Index("ix_videos_user_id", "user_id"),
        Index("ix_videos_camera_id", "camera_id"),
        Index("ix_videos_status", "status"),
        Index("ix_videos_expires_at", "expires_at"),
        Index("ix_videos_created_status", "created_at", "status"),
        Index("ix_videos_analysis_result", "analysis_result"),
    )

    def set_video_ttl(self) -> None:
        self.set_ttl(VIDEO_TTL_HOURS)

    def mark_ready(self) -> None:
        self.status = VideoStatus.READY.value if hasattr(VideoStatus.READY, "value") else str(VideoStatus.READY)

    def mark_analyzing(self) -> None:
        self.status = (
            VideoStatus.ANALYZING.value if hasattr(VideoStatus.ANALYZING, "value") else str(VideoStatus.ANALYZING)
        )

    def mark_analyzed(self, result: AnalysisResult) -> None:
        self.status = (
            VideoStatus.ANALYZED.value if hasattr(VideoStatus.ANALYZED, "value") else str(VideoStatus.ANALYZED)
        )
        self.analysis_result = result.value if hasattr(result, "value") else str(result)
        self.analysis_completed_at = datetime.utcnow()

    def get_storage_path(self) -> str:
        return os.path.join(STORAGE_BASE_PATH, self.filepath)

