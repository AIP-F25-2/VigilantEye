from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class TicketHistory(BaseModel):
    __tablename__ = "ticket_history"

    ticket_id = Column(CHAR(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    event = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="history")

    __table_args__ = (Index("ix_ticket_history_ticket_id", "ticket_id"),)

