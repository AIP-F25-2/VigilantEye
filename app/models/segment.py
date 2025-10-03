from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class SegmentStatus(enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class Segment(BaseModel):
    """Video segment model"""
    __tablename__ = 'segments'
    
    # Segment details
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    segment_index = db.Column(db.Integer, nullable=False)
    
    # Timing
    start_seconds = db.Column(db.Float, nullable=False)
    end_seconds = db.Column(db.Float, nullable=False)
    duration_seconds = db.Column(db.Float, nullable=False)
    
    # File properties
    file_size = db.Column(db.BigInteger, nullable=False)
    file_size_human = db.Column(db.String(50), nullable=False)
    
    # Video properties
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    fps = db.Column(db.Float, nullable=True)
    bitrate = db.Column(db.Integer, nullable=True)
    
    # Processing
    status = db.Column(db.Enum(SegmentStatus), default=SegmentStatus.PROCESSING)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Segment settings
    segment_seconds = db.Column(db.Float, nullable=False)  # Original segment duration
    keyframe_interval = db.Column(db.Integer, nullable=True)
    
    # Metadata
    segment_metadata = db.Column(JSON, default=dict)
    
    # Relationships
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    def __repr__(self):
        return f'<Segment {self.filename} (#{self.segment_index})>'
    
    def to_dict(self):
        """Convert segment to dictionary"""
        data = super().to_dict()
        data['status'] = self.status.value if self.status else None
        return data
