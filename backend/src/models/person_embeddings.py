"""Person embeddings database models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class PersonType(str, enum.Enum):
    """Person identification type."""
    
    FACE_BASED = "FACE_BASED"
    CLOTHING_BASED = "CLOTHING_BASED"
    COMBINED = "COMBINED"


class PersonEmbedding(Base):
    """Person embeddings for identification."""

    __tablename__ = "person_embeddings"

    # Person identification
    person_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique person identifier"
    )
    person_type: Mapped[PersonType] = mapped_column(
        Enum(PersonType),
        nullable=False,
        index=True,
        comment="Type of person identification"
    )
    
    # Face-based identification
    face_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Associated face ID if face-based"
    )
    face_embedding: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Face embedding vector (JSON)"
    )
    face_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Face recognition confidence"
    )
    
    # Clothing-based identification
    clothing_signature: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Clothing signature for matching"
    )
    clothing_embedding: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Clothing embedding vector (JSON)"
    )
    clothing_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Clothing recognition confidence"
    )
    
    # Appearance metadata
    appearance_metadata: Mapped[Optional[str]] = mapped_column(
        JSON,
        nullable=True,
        comment="Clothing and appearance analysis results"
    )
    
    # Demographics (from face analysis)
    estimated_age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated age"
    )
    age_range: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Age range (e.g., 20-29)"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Estimated gender"
    )
    gender_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Gender estimation confidence"
    )
    ethnicity: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Estimated ethnicity"
    )
    
    # Clothing details
    dominant_clothing_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Dominant clothing type"
    )
    dominant_color: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Dominant clothing color"
    )
    dominant_texture: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Dominant texture pattern"
    )
    
    # Tracking information
    first_seen_video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="First video where person was seen"
    )
    first_seen_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="First appearance timestamp"
    )
    last_seen_video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Last video where person was seen"
    )
    last_seen_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Last appearance timestamp"
    )
    
    # Statistics
    total_appearances: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Total number of appearances"
    )
    unique_videos: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of unique videos where person appeared"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether person is still being tracked"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonEmbedding(person_id={self.person_id}, type={self.person_type})>"


class PersonAppearance(Base):
    """Individual person appearances in videos."""

    __tablename__ = "person_appearances"

    # Person reference
    person_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("person_embeddings.person_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Person identifier"
    )
    
    # Video reference
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Video where person appeared"
    )
    
    # Appearance details
    frame_timestamp_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Frame timestamp in video"
    )
    processing_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Processing batch ID"
    )
    
    # Bounding box
    bounding_box_x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Bounding box X coordinate"
    )
    bounding_box_y: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Bounding box Y coordinate"
    )
    bounding_box_width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Bounding box width"
    )
    bounding_box_height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Bounding box height"
    )
    
    # Detection confidence
    detection_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Detection confidence score"
    )
    
    # Face information (if available)
    face_detected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether face was detected"
    )
    face_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Face detection confidence"
    )
    
    # Clothing information
    clothing_signature: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Clothing signature at this appearance"
    )
    clothing_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Clothing recognition confidence"
    )
    
    # Appearance metadata
    appearance_metadata: Mapped[Optional[str]] = mapped_column(
        JSON,
        nullable=True,
        comment="Detailed appearance analysis"
    )
    
    # File references
    image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Path to cropped person image"
    )
    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to thumbnail image"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonAppearance(person_id={self.person_id}, video_id={self.video_id}, timestamp={self.frame_timestamp_ms})>"


class PersonMatch(Base):
    """Person matching results between different appearances."""

    __tablename__ = "person_matches"

    # Source appearance
    source_person_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("person_embeddings.person_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source person ID"
    )
    source_appearance_id: Mapped[int] = mapped_column(
        ForeignKey("person_appearances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source appearance ID"
    )
    
    # Target appearance
    target_person_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("person_embeddings.person_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target person ID"
    )
    target_appearance_id: Mapped[int] = mapped_column(
        ForeignKey("person_appearances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target appearance ID"
    )
    
    # Match details
    match_type: Mapped[PersonType] = mapped_column(
        Enum(PersonType),
        nullable=False,
        comment="Type of match (face/clothing/combined)"
    )
    match_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Match confidence score"
    )
    match_distance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Distance between embeddings"
    )
    
    # Match metadata
    match_metadata: Mapped[Optional[str]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional match information"
    )
    
    # Status
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether match has been manually verified"
    )
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who verified the match"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When match was verified"
    )

    def __repr__(self) -> str:
        return f"<PersonMatch(source={self.source_person_id}, target={self.target_person_id}, confidence={self.match_confidence})>"
