"""AI Analysis models for storing results."""

import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class AnalysisStatus(str, enum.Enum):
    """Analysis status enumeration."""
    
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ThreatLevel(str, enum.Enum):
    """Threat level enumeration."""
    
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AudioAnalysis(Base):
    """Audio analysis results."""

    __tablename__ = "audio_analysis"

    # References
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    storage_file_id: Mapped[int] = mapped_column(
        ForeignKey("storage_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # Audio classification results
    sound_classification: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of detected sounds with confidence scores"
    )
    dominant_sounds: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Comma-separated list of dominant sounds"
    )
    
    # Speech-to-text results
    transcription: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full text transcription"
    )
    language_detected: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus),
        default=AnalysisStatus.PENDING,
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<AudioAnalysis(id={self.id}, video_id={self.video_id}, status={self.status.value})>"


class FaceDetection(Base):
    """Face detection and recognition results."""

    __tablename__ = "face_detections"

    # References
    frame_storage_id: Mapped[int] = mapped_column(
        ForeignKey("storage_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # Face information
    face_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique identifier for this face across frames"
    )
    
    # Detection details
    bounding_box: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="JSON: {x, y, width, height}"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Demographics
    estimated_age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    age_range: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g., '25-35'"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    gender_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Physical attributes
    skin_tone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    facial_expression: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g., 'happy', 'sad', 'neutral'"
    )
    emotion_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Accessories
    wearing_glasses: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True
    )
    wearing_mask: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True
    )
    
    # Vector embedding for face recognition
    vector_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Reference to vector in vector DB"
    )
    
    # Frame context
    frame_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Timestamp in video"
    )

    def __repr__(self) -> str:
        return f"<FaceDetection(id={self.id}, face_id={self.face_id}, age={self.estimated_age})>"


class ImageAnalysis(Base):
    """Image/Frame analysis results."""

    __tablename__ = "image_analysis"

    # References
    frame_storage_id: Mapped[int] = mapped_column(
        ForeignKey("storage_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    frame_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # Environment analysis
    scene_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Overall scene description"
    )
    location_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g., 'indoor', 'outdoor', 'office', 'street'"
    )
    time_of_day: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="e.g., 'daytime', 'nighttime', 'dusk'"
    )
    weather_conditions: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g., 'sunny', 'rainy', 'cloudy'"
    )
    lighting_quality: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Text detection (OCR)
    detected_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="All text found in image"
    )
    text_locations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of text bounding boxes"
    )

    # Object detection
    detected_objects: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of objects with bounding boxes and confidence"
    )
    object_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    
    # Activity detection
    detected_activities: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of detected activities"
    )

    # People count
    people_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    vehicle_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Combined description
    combined_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated comprehensive description"
    )

    # Status
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus),
        default=AnalysisStatus.PENDING,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<ImageAnalysis(id={self.id}, video_id={self.video_id}, objects={self.object_count})>"


class ThreatAssessment(Base):
    """Threat and emergency detection results."""

    __tablename__ = "threat_assessments"

    # References
    frame_storage_id: Mapped[int] = mapped_column(
        ForeignKey("storage_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    image_analysis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("image_analysis.id", ondelete="CASCADE"),
        nullable=True
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    frame_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # Threat assessment
    is_threat: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    threat_level: Mapped[ThreatLevel] = mapped_column(
        Enum(ThreatLevel),
        default=ThreatLevel.SAFE,
        nullable=False,
        index=True
    )
    threat_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Threat details
    threat_types: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Comma-separated: weapon, violence, fire, accident, etc."
    )
    threat_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="LLM-generated threat description"
    )

    # Emergency detection
    is_emergency: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    emergency_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g., 'medical', 'fire', 'accident', 'violence'"
    )

    # Evidence storage
    evidence_stored: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    evidence_storage_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("storage_files.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to stored evidence file"
    )
    evidence_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Recommendations
    recommended_action: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="e.g., 'Alert security', 'Call emergency', 'Monitor'"
    )
    priority_level: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="1-10, higher means more urgent"
    )

    # Notification
    alert_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    alert_sent_at: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ThreatAssessment(id={self.id}, threat={self.is_threat}, "
            f"level={self.threat_level.value})>"
        )


class FaceVector(Base):
    """Face vectors for similarity search."""

    __tablename__ = "face_vectors"

    face_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Vector DB reference
    vector_db_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="ID in vector database (e.g., ChromaDB)"
    )
    
    # Aggregated information from all detections
    first_seen_video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    last_seen_video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False
    )
    
    appearance_count: Mapped[int] = mapped_column(
        Integer,
        default=1
    )
    
    # Average demographics
    avg_estimated_age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    primary_gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Labels
    person_label: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User-assigned label for this person"
    )
    is_person_of_interest: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<FaceVector(id={self.id}, face_id={self.face_id}, count={self.appearance_count})>"
