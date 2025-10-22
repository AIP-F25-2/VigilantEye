"""Storage models for tracking files with TTL."""

import enum
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class FileType(str, enum.Enum):
    """File type enumeration."""
    
    VIDEO = "VIDEO"
    FRAME = "FRAME"
    AUDIO = "AUDIO"
    THUMBNAIL = "THUMBNAIL"
    OTHER = "OTHER"


class StorageStatus(str, enum.Enum):
    """Storage status enumeration."""
    
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"
    PENDING_DELETION = "PENDING_DELETION"


class StorageFile(Base):
    """Storage file tracking with TTL."""

    __tablename__ = "storage_files"

    # References
    video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Associated video ID"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user ID"
    )

    # Processing reference
    processing_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Processing batch ID"
    )

    # File information
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="File name"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Full path to file"
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

    # Metadata
    metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON metadata about the file"
    )

    # TTL and status
    ttl_hours: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Time to live in hours"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="When file should be deleted"
    )
    status: Mapped[StorageStatus] = mapped_column(
        Enum(StorageStatus),
        default=StorageStatus.ACTIVE,
        nullable=False,
        index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When file was actually deleted"
    )

    # Additional info
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="MD5 or SHA256 checksum"
    )
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether file has been processed"
    )

    def __repr__(self) -> str:
        return (
            f"<StorageFile(id={self.id}, type={self.file_type.value}, "
            f"filename={self.filename}, expires={self.expires_at})>"
        )

    def is_expired(self) -> bool:
        """Check if file has expired."""
        return datetime.utcnow() >= self.expires_at

    def extend_ttl(self, hours: int) -> None:
        """Extend TTL by specified hours."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.ttl_hours = hours

    @property
    def time_remaining(self) -> Optional[timedelta]:
        """Get time remaining until expiration."""
        if self.status == StorageStatus.DELETED:
            return None
        now = datetime.utcnow()
        if now >= self.expires_at:
            return timedelta(0)
        return self.expires_at - now
