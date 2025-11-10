import os
from typing import Any, Dict

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from src.config.constants import EvidenceType
from src.models.base import BaseModel

_config = get_config()
EVIDENCE_STORAGE_BASE_PATH = getattr(_config, "EVIDENCE_STORAGE_BASE_PATH", _config.STORAGE_BASE_PATH)


class Evidence(BaseModel):
    __tablename__ = "evidence"

    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    ticket_id = Column(CHAR(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(20), nullable=False)
    filepath = Column(String(500), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    frame_number = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    is_flagged = Column(Boolean, nullable=False, default=True)
    confidence_score = Column(Float, nullable=True)

    video = relationship("Video", back_populates="evidence")
    ticket = relationship("Ticket", back_populates="evidence")

    __table_args__ = (
        CheckConstraint(
            "type IN ('frame', 'audio', 'video')",
            name="ck_evidence_type_valid",
        ),
        Index("ix_evidence_ticket_id", "ticket_id"),
        Index("ix_evidence_video_id", "video_id"),
        Index("ix_evidence_type", "type"),
        Index("ix_evidence_ticket_timestamp", "ticket_id", "timestamp"),
        Index("ix_evidence_is_flagged", "is_flagged"),
    )

    def get_storage_path(self) -> str:
        return os.path.join(EVIDENCE_STORAGE_BASE_PATH, self.filepath)

    def get_ai_analysis_summary(self) -> Dict[str, Any]:
        if not self.ai_analysis:
            return {}
        summary_keys = ("scene", "persons", "objects", "audio", "llm_reasoning")
        return {key: self.ai_analysis.get(key) for key in summary_keys if key in self.ai_analysis}

    def mark_reviewed(self) -> None:
        self.is_flagged = False

