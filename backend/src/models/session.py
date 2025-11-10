from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class Session(BaseModel):
    __tablename__ = "sessions"

    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(String(500), nullable=False, unique=True)
    refresh_token = Column(String(500), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        back_populates="sessions",
        foreign_keys="Session.user_id",
    )

    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", "is_active"),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = datetime.utcnow()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def is_refresh_expired(self) -> bool:
        return datetime.utcnow() > self.refresh_expires_at

    def refresh(self, new_access_token: str, new_expires_at: datetime) -> None:
        self.access_token = new_access_token
        self.expires_at = new_expires_at

