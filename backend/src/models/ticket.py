from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.config import get_config
from src.config.constants import TicketPriority, TicketStatus, ThreatLevel
from src.models.base import BaseModel
from src.models.associations import ticket_persons

_config = get_config()
TICKET_AUTO_CLOSE_HOURS = _config.TICKET_AUTO_CLOSE_HOURS
TICKET_ESCALATION_TIMEOUT_MINUTES = _config.TICKET_ESCALATION_TIMEOUT_MINUTES


def _enum_value(member: Any) -> str:
    return member.value if hasattr(member, "value") else str(member)


class Ticket(BaseModel):
    __tablename__ = "tickets"

    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default=_enum_value(TicketPriority.MEDIUM))
    status = Column(String(20), nullable=False, default=_enum_value(TicketStatus.OPEN))
    threat_level = Column(String(20), nullable=True)
    assigned_to = Column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    escalated = Column(Boolean, nullable=False, default=False)
    escalation_count = Column(Integer, nullable=False, default=0)
    escalation_sent_at = Column(DateTime, nullable=True)
    sla_breach = Column(Boolean, nullable=False, default=False)
    auto_close_at = Column(DateTime, nullable=True)

    video = relationship("Video", back_populates="tickets")
    assigned_user = relationship(
        "User",
        back_populates="tickets_assigned",
        foreign_keys=[assigned_to],
    )
    creator = relationship(
        "User",
        back_populates="tickets_created",
        foreign_keys=[created_by],
    )
    evidence = relationship(
        "Evidence",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    persons_of_interest = relationship(
        "Person",
        secondary=ticket_persons,
        back_populates="tickets",
    )
    history = relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'in_progress', 'resolved', 'closed')",
            name="ck_tickets_status_valid",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_tickets_priority_valid",
        ),
        CheckConstraint(
            "threat_level IS NULL OR threat_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_tickets_threat_level_valid",
        ),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_assigned_to", "assigned_to"),
        Index("ix_tickets_created_at", "created_at"),
        Index("ix_tickets_auto_close_at", "auto_close_at"),
        Index("ix_tickets_status_priority_created", "status", "priority", "created_at"),
        Index("ix_tickets_escalated", "escalated"),
        Index("ix_tickets_sla_breach", "sla_breach"),
    )

    def acknowledge(self, user_id: str | None) -> None:
        self.status = _enum_value(TicketStatus.ACKNOWLEDGED)
        self.acknowledged_at = datetime.utcnow()
        self.assigned_to = user_id

    def close(self, user_id: str | None = None) -> None:
        self.status = _enum_value(TicketStatus.CLOSED)
        self.closed_at = datetime.utcnow()
        if user_id:
            self.assigned_to = user_id

    def escalate(self) -> None:
        self.escalated = True
        self.escalation_count = (self.escalation_count or 0) + 1
        self.escalation_sent_at = datetime.utcnow()

    def check_sla_breach(self) -> bool:
        if self.acknowledged_at:
            return False
        breach_threshold = timedelta(minutes=TICKET_ESCALATION_TIMEOUT_MINUTES)
        if datetime.utcnow() - self.created_at > breach_threshold:
            self.sla_breach = True
            return True
        return False

    def is_auto_closable(self) -> bool:
        return (
            self.auto_close_at is not None
            and datetime.utcnow() > self.auto_close_at
            and self.status != _enum_value(TicketStatus.CLOSED)
        )

    def get_response_time(self) -> float | None:
        if not self.acknowledged_at:
            return None
        return (self.acknowledged_at - self.created_at).total_seconds()

    def get_resolution_time(self) -> float | None:
        if not self.closed_at:
            return None
        return (self.closed_at - self.created_at).total_seconds()

    def set_auto_close_deadline(self) -> None:
        self.auto_close_at = self.created_at + timedelta(hours=TICKET_AUTO_CLOSE_HOURS)

