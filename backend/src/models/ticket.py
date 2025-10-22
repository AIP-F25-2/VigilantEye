"""Ticket management models."""

import enum
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class TicketStatus(str, enum.Enum):
    """Ticket status enumeration."""
    
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    AUTO_CLOSED = "AUTO_CLOSED"


class TicketPriority(str, enum.Enum):
    """Ticket priority enumeration."""
    
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Ticket(Base):
    """Ticket for threat management."""

    __tablename__ = "tickets"

    # Threat reference
    threat_assessment_id: Mapped[int] = mapped_column(
        ForeignKey("threat_assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Associated threat assessment"
    )
    
    # Ticket details
    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique ticket identifier (e.g., TKT-20240115-001)"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Ticket title"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full threat description"
    )
    
    # Status and priority
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True
    )
    
    # Timestamps
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    escalated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    auto_close_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When ticket will auto-close"
    )
    
    # Assignment
    acknowledged_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    closed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Video/Frame reference
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    frame_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    # Evidence
    evidence_folder_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to evidence folder"
    )
    evidence_report_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to evidence report"
    )
    total_evidence_files: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # Telegram integration
    telegram_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Telegram message ID for updates"
    )
    telegram_channel: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Channel where message was sent (primary/escalation)"
    )
    escalation_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Escalation message ID"
    )
    
    # Metrics
    acknowledgment_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time taken to acknowledge in seconds"
    )
    resolution_time_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time taken to close in seconds"
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes/comments"
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Soft delete timestamp"
    )

    def __repr__(self) -> str:
        return f"<Ticket(number={self.ticket_number}, status={self.status.value}, priority={self.priority.value})>"

    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue for auto-close."""
        return datetime.utcnow() >= self.auto_close_at

    @property
    def time_until_auto_close(self) -> timedelta:
        """Get time remaining until auto-close."""
        return self.auto_close_at - datetime.utcnow()


class TicketEvidence(Base):
    """Evidence files linked to tickets."""

    __tablename__ = "ticket_evidence"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # File reference
    storage_file_id: Mapped[int] = mapped_column(
        ForeignKey("storage_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Evidence details
    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type: original, related_frame, report"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Face matching (if related frame)
    matched_face_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Face ID that matched"
    )
    match_confidence: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Face match confidence score"
    )
    
    # Frame details
    source_video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"),
        nullable=True
    )
    frame_timestamp_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<TicketEvidence(ticket_id={self.ticket_id}, type={self.evidence_type}, file={self.file_name})>"


class TicketActivity(Base):
    """Activity log for ticket actions."""

    __tablename__ = "ticket_activity"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action: created, acknowledged, escalated, closed, etc."
    )
    
    old_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    new_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON metadata for action"
    )

    def __repr__(self) -> str:
        return f"<TicketActivity(ticket_id={self.ticket_id}, action={self.action})>"
