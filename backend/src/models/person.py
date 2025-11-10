from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from src.config import get_config
from src.models.associations import ticket_persons
from src.models.base import BaseModel, TTLMixin

_config = get_config()
PERSON_VECTOR_TTL_HOURS = _config.PERSON_VECTOR_TTL_HOURS


class Person(TTLMixin, BaseModel):
    __tablename__ = "persons"
    __allow_unmapped__ = True

    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    person_tracking_id = Column(String(50), nullable=False)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    total_appearances = Column(Integer, nullable=False, default=1)
    age_estimate = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    ethnicity = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    clothing_description = Column(Text, nullable=True)
    body_features = Column(JSON, nullable=True)

    video = relationship("Video", back_populates="persons")
    tickets = relationship(
        "Ticket",
        secondary=ticket_persons,
        back_populates="persons_of_interest",
    )

    __table_args__ = (
        Index("ix_persons_video_id", "video_id"),
        Index("ix_persons_tracking_id", "person_tracking_id"),
        Index("ix_persons_expires_at", "expires_at"),
        Index("ix_persons_video_first_seen", "video_id", "first_seen"),
        Index("ix_persons_confidence", "confidence_score"),
    )

    def set_person_ttl(self) -> None:
        self.set_ttl(PERSON_VECTOR_TTL_HOURS)

    def update_last_seen(self, timestamp: datetime) -> None:
        self.last_seen = timestamp
        self.total_appearances = (self.total_appearances or 0) + 1

    def get_duration(self) -> float | None:
        if not self.first_seen or not self.last_seen:
            return None
        return (self.last_seen - self.first_seen).total_seconds()

    def to_dict_with_embeddings(self) -> Dict[str, Any]:
        data = self.to_dict()
        data["embeddings"] = {
            "face": [],
            "body": [],
        }
        return data

