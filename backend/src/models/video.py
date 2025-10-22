"""Video model."""

import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class VideoStatus(str, enum.Enum):
    """Video processing status enumeration."""
    
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STREAMING = "STREAMING"


class Video(Base):
    """Video model for storing video metadata and processing status."""

    __tablename__ = "videos"

    # User relationship
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # File information
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique filename on disk"
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original uploaded filename"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full path to video file"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="File size in bytes"
    )
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Video metadata
    duration: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Video duration in seconds"
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    fps: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Frames per second"
    )
    codec: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Processing status
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus),
        default=VideoStatus.UPLOADED,
        nullable=False
    )
    
    # Thumbnail
    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Analysis results (JSON stored as text)
    analysis_results: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON string of analysis results"
    )

    # Stream metadata
    is_stream: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this is a camera stream"
    )
    stream_metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON string of stream metadata"
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, filename={self.filename}, status={self.status.value})>"
