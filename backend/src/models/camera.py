from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class Camera(BaseModel):
    __tablename__ = "cameras"

    name = Column(String(100), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    stream_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    last_active = Column(DateTime, nullable=True)

    videos = relationship("Video", back_populates="camera")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance')",
            name="ck_cameras_status_valid",
        ),
        Index("ix_cameras_status", "status"),
    )

    def mark_active(self) -> None:
        self.status = "active"
        self.last_active = datetime.utcnow()

    def mark_inactive(self) -> None:
        self.status = "inactive"

    def is_live_stream(self) -> bool:
        return self.stream_url is not None

