"""
FaceAi Database Models for VIGILANTEye
Stores face detection, demographics, and ambiguity analysis results
"""

from app import db
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean, ForeignKey
from sqlalchemy import func
from datetime import datetime
import uuid

def gen_uuid():
    return str(uuid.uuid4())

class FaceDetection(db.Model):
    """Store face detection results"""
    __tablename__ = "face_detections"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    source_type = Column(String(20), nullable=False)  # 'image', 'video_frame', 'camera'
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)  # Foreign key to videos table
    frame_number = Column(Integer, nullable=True)
    
    # Detection results
    faces_detected = Column(Integer, default=0)
    detection_results = Column(JSON, nullable=True)  # Full detection data
    annotated_image_path = Column(String(500), nullable=True)
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, default=0.35)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "faces_detected": self.faces_detected,
            "detection_results": self.detection_results,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class DemographicsAnalysis(db.Model):
    """Store demographics analysis results"""
    __tablename__ = "demographics_analyses"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    face_detection_id = Column(String(36), ForeignKey('face_detections.id'), nullable=True)
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    
    # Demographics results
    faces_analyzed = Column(Integer, default=0)
    analysis_results = Column(JSON, nullable=True)  # Full analysis data
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "face_detection_id": self.face_detection_id,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "faces_analyzed": self.faces_analyzed,
            "analysis_results": self.analysis_results,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class AmbiguityAnalysis(db.Model):
    """Store ambiguity analysis results"""
    __tablename__ = "ambiguity_analyses"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    image1_path = Column(String(500), nullable=False)
    image2_path = Column(String(500), nullable=False)
    source_type = Column(String(20), default='comparison')
    
    # Analysis results
    is_ambiguous = Column(Boolean, default=False)
    ambiguity_score = Column(Float, nullable=False)
    similarity_scores = Column(JSON, nullable=True)  # Individual similarity scores
    reasons = Column(JSON, nullable=True)  # List of reasons for ambiguity
    weights = Column(JSON, nullable=True)  # Weighting used in analysis
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    threshold_used = Column(Float, default=0.7)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "image1_path": self.image1_path,
            "image2_path": self.image2_path,
            "is_ambiguous": self.is_ambiguous,
            "ambiguity_score": self.ambiguity_score,
            "similarity_scores": self.similarity_scores,
            "reasons": self.reasons,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version,
            "threshold_used": self.threshold_used
        }

class FaceEncoding(db.Model):
    """Store face encodings for recognition"""
    __tablename__ = "face_encodings"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Face information
    person_id = Column(String(100), nullable=False)  # Person identifier
    face_detection_id = Column(String(36), ForeignKey('face_detections.id'), nullable=True)
    source_path = Column(String(500), nullable=True)
    
    # Encoding data
    face_encoding = Column(JSON, nullable=False)  # Face encoding as JSON array
    bounding_box = Column(JSON, nullable=True)  # Face bounding box coordinates
    similarity_threshold = Column(Float, default=0.35)
    
    # Metadata
    is_known_person = Column(Boolean, default=True)
    confidence_score = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "person_id": self.person_id,
            "face_detection_id": self.face_detection_id,
            "source_path": self.source_path,
            "bounding_box": self.bounding_box,
            "is_known_person": self.is_known_person,
            "confidence_score": self.confidence_score,
            "model_version": self.model_version
        }

class FaceAiConfiguration(db.Model):
    """Store FaceAi configuration settings"""
    __tablename__ = "faceai_configurations"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Configuration settings
    config_name = Column(String(100), nullable=False, unique=True)
    config_data = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "config_name": self.config_name,
            "config_data": self.config_data,
            "is_active": self.is_active,
            "description": self.description,
            "created_by": self.created_by
        }
