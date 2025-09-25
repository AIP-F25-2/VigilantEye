from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, JSON
from sqlalchemy import func
from sqlalchemy.dialects.mysql import BIGINT
import enum
import uuid
from .db import Base

class MessageStatus(enum.Enum):
    initiated = "initiated"
    sent = "sent"
    acknowledged = "acknowledged"
    escalated = "escalated"
    closed = "closed"

def gen_uuid():
    return str(uuid.uuid4())

class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    id = Column(String(36), primary_key=True, default=gen_uuid)  # uuid
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # original payload
    source_type = Column(String(20), nullable=False)  # 'text' or 'image'
    content = Column(Text, nullable=False)  # text message or image URL or base64 reference
    source_channel = Column(String(64), nullable=True)  # channel provided in input

    # Telegram specifics
    telegram_chat_id = Column(String(64), nullable=True)  # where it was sent
    telegram_message_id = Column(Integer, nullable=True)

    status = Column(Enum(MessageStatus), default=MessageStatus.initiated, nullable=False)
    meta = Column(JSON, nullable=True)  # free-form: input raw, acknowledger info etc.

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status.value if self.status else None
        }
