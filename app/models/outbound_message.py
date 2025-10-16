from app import db
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, JSON
from sqlalchemy import func
import enum
import uuid
from datetime import datetime

class MessageStatus(enum.Enum):
    initiated = "initiated"
    sent = "sent"
    acknowledged = "acknowledged"
    escalated = "escalated"
    closed = "closed"

def gen_uuid():
    return str(uuid.uuid4())

class OutboundMessage(db.Model):
    """OutboundMessage model for Telegram integration"""
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
        """Convert model instance to dictionary"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "source_type": self.source_type,
            "content": self.content,
            "source_channel": self.source_channel,
            "telegram_chat_id": self.telegram_chat_id,
            "telegram_message_id": self.telegram_message_id,
            "status": self.status.value if self.status else None,
            "meta": self.meta
        }
    
    def save(self):
        """Save the model instance to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete the model instance from database"""
        db.session.delete(self)
        db.session.commit()
        return True
