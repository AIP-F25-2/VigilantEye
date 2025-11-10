from typing import Any, Dict

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="success")
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs", foreign_keys="AuditLog.user_id")

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failure', 'error')",
            name="ck_audit_logs_status_valid",
        ),
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_status", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()

    def get_details_summary(self) -> Dict[str, Any]:
        if not self.details:
            return {}
        summary_keys = ("old_value", "new_value", "changed_by", "reason")
        return {key: self.details.get(key) for key in summary_keys if key in self.details}

