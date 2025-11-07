"""Domain models and database entities."""

from src.database.base import Base

# Core models
from .user import User, UserRole
from .video import Video, VideoStatus
from .storage import StorageFile, FileType, StorageStatus

# AI Analysis models
from .ai_analysis import (
    AudioAnalysis,
    FaceDetection,
    ImageAnalysis,
    ThreatAssessment,
    FaceVector,
    AnalysisStatus,
    ThreatLevel,
)

# Person tracking models
from .person_embeddings import (
    PersonEmbedding,
    PersonAppearance,
    PersonMatch,
    PersonType,
)

# Ticket management models
from .ticket import (
    Ticket,
    TicketEvidence,
    TicketActivity,
    TicketStatus,
    TicketPriority,
)

__all__ = [
    # Base
    "Base",
    # Core models
    "User",
    "UserRole",
    "Video",
    "VideoStatus",
    "StorageFile",
    "FileType",
    "StorageStatus",
    # AI Analysis models
    "AudioAnalysis",
    "FaceDetection",
    "ImageAnalysis",
    "ThreatAssessment",
    "FaceVector",
    "AnalysisStatus",
    "ThreatLevel",
    # Person tracking models
    "PersonEmbedding",
    "PersonAppearance",
    "PersonMatch",
    "PersonType",
    # Ticket management models
    "Ticket",
    "TicketEvidence",
    "TicketActivity",
    "TicketStatus",
    "TicketPriority",
]

# Import all models to ensure they're registered with SQLAlchemy metadata
# This is critical for migrations to work correctly
