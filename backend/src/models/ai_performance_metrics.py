from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AIPerformanceMetrics(BaseModel):
    """Track AI model performance metrics for monitoring and optimization."""

    __tablename__ = "ai_performance_metrics"

    video_id = Column(CHAR(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=True, index=True)
    task_name = Column(String(100), nullable=False, index=True)
    model_name = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # 'success', 'failure', 'partial'
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional context: frame_count, audio_duration, etc.

    # Relationships
    video = relationship("Video", backref="ai_performance_metrics")

    __table_args__ = (
        Index("ix_ai_performance_metrics_task_name", "task_name"),
        Index("ix_ai_performance_metrics_created_at", "created_at"),
        Index("ix_ai_performance_metrics_task_created", "task_name", "created_at"),
    )

    def to_dict(self, exclude: Optional[list] = None) -> dict:
        """Serialize to dictionary for API responses."""
        exclude = exclude or []
        data = super().to_dict(exclude=exclude)
        return data

    @classmethod
    def get_average_duration(cls, task_name: str) -> Optional[float]:
        """Calculate average duration for a task type."""
        from sqlalchemy import func
        from src.app import db

        result = (
            db.session.query(func.avg(cls.duration_ms))
            .filter(cls.task_name == task_name, cls.status == "success", cls.is_deleted == False)
            .scalar()
        )
        return float(result) if result else None

