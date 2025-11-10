from datetime import datetime

import bcrypt
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, String
from sqlalchemy.orm import relationship

from src.config.constants import UserRole
from src.models.base import BaseModel


def _enum_value(role: UserRole) -> str:
    return role.value if hasattr(role, "value") else str(role)


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String(80), nullable=False, unique=True)
    email = Column(String(120), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=_enum_value(UserRole.STAFF))
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime, nullable=True)

    videos = relationship("Video", back_populates="uploader")
    tickets_assigned = relationship(
        "Ticket",
        back_populates="assigned_user",
        foreign_keys="Ticket.assigned_to",
    )
    tickets_created = relationship(
        "Ticket",
        back_populates="creator",
        foreign_keys="Ticket.created_by",
    )
    sessions = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        CheckConstraint(
            f"role IN ('{_enum_value(UserRole.STAFF)}', '{_enum_value(UserRole.ADMIN)}')",
            name="ck_users_role_valid",
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_active_not_deleted", "is_active", "is_deleted"),
    )

    def set_password(self, password: str) -> None:
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    def update_last_login(self) -> None:
        self.last_login = datetime.utcnow()

