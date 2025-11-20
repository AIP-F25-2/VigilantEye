"""
Database models for AI Analytics features
"""

from app import db
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
import uuid
from datetime import datetime

def gen_uuid():
    return str(uuid.uuid4())

class ObjectDetection(db.Model):
    """Store object detection results"""
    __tablename__ = "object_detections"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    source_type = Column(String(20), nullable=False)  # 'image', 'video_frame', 'camera'
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)
    frame_number = Column(Integer, nullable=True)
    camera_id = Column(String(100), nullable=True)
    
    # Detection results
    objects_detected = Column(Integer, default=0)
    detection_results = Column(JSON, nullable=True)  # Full detection data
    annotated_image_path = Column(String(500), nullable=True)
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, default=0.3)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "camera_id": self.camera_id,
            "objects_detected": self.objects_detected,
            "detection_results": self.detection_results,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class AnomalyDetection(db.Model):
    """Store anomaly detection results"""
    __tablename__ = "anomaly_detections"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)
    frame_number = Column(Integer, nullable=True)
    camera_id = Column(String(100), nullable=True)
    
    # Anomaly details
    anomaly_type = Column(String(50), nullable=False)  # unusual_motion, loitering, etc.
    confidence = Column(Float, nullable=False)
    location = Column(JSON, nullable=True)  # [x, y] coordinates
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Alert status
    is_alert = Column(Boolean, default=True)
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "camera_id": self.camera_id,
            "anomaly_type": self.anomaly_type,
            "confidence": self.confidence,
            "location": self.location,
            "description": self.description,
            "metadata": self.metadata_json,
            "is_alert": self.is_alert,
            "alert_sent": self.alert_sent,
            "alert_sent_at": self.alert_sent_at.isoformat() if self.alert_sent_at else None,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class BehaviorAnalysis(db.Model):
    """Store behavior analysis results"""
    __tablename__ = "behavior_analyses"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)
    frame_number = Column(Integer, nullable=True)
    camera_id = Column(String(100), nullable=True)
    
    # Behavior details
    behavior_type = Column(String(50), nullable=False)  # walking, running, loitering, etc.
    confidence = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    location = Column(JSON, nullable=True)  # [x, y] coordinates
    metadata_json = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "camera_id": self.camera_id,
            "behavior_type": self.behavior_type,
            "confidence": self.confidence,
            "duration_seconds": self.duration_seconds,
            "location": self.location,
            "metadata": self.metadata_json,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class CrowdDensityAnalysis(db.Model):
    """Store crowd density analysis results"""
    __tablename__ = "crowd_density_analyses"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Source information
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)
    frame_number = Column(Integer, nullable=True)
    camera_id = Column(String(100), nullable=True)
    
    # Density analysis
    density_level = Column(String(20), nullable=False)  # low, medium, high, very_high
    person_count = Column(Integer, default=0)
    density_percentage = Column(Float, nullable=False)
    high_density_areas = Column(JSON, nullable=True)  # List of areas with high density
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "camera_id": self.camera_id,
            "density_level": self.density_level,
            "person_count": self.person_count,
            "density_percentage": self.density_percentage,
            "high_density_areas": self.high_density_areas,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version
        }

class SmartAlert(db.Model):
    """Store smart alerts generated by AI"""
    __tablename__ = "smart_alerts"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # anomaly, behavior, crowd, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Source information
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    video_id = Column(String(36), nullable=True)
    frame_number = Column(Integer, nullable=True)
    camera_id = Column(String(100), nullable=True)
    
    # Related detections
    anomaly_detection_id = Column(String(36), ForeignKey('anomaly_detections.id'), nullable=True)
    behavior_analysis_id = Column(String(36), ForeignKey('behavior_analyses.id'), nullable=True)
    
    # Alert status
    is_read = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    
    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "camera_id": self.camera_id,
            "anomaly_detection_id": self.anomaly_detection_id,
            "behavior_analysis_id": self.behavior_analysis_id,
            "is_read": self.is_read,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "notification_sent": self.notification_sent,
            "notification_sent_at": self.notification_sent_at.isoformat() if self.notification_sent_at else None,
            "metadata": self.metadata_json
        }

