from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class ClipStatus(enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class Clip(BaseModel):
    """Video clip model"""
    __tablename__ = 'clips'
    
    # Clip details
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    
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
    status = db.Column(db.Enum(ClipStatus), default=ClipStatus.PROCESSING)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Watermark and effects
    watermark_text = db.Column(db.String(500), nullable=True)
    watermark_position = db.Column(db.String(50), default='bottom-right')
    effects = db.Column(JSON, default=dict)
    
    # Metadata
    clip_metadata = db.Column(JSON, default=dict)
    
    # Relationships
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    def __repr__(self):
        return f'<Clip {self.filename} ({self.start_seconds}s-{self.end_seconds}s)>'
    
    def to_dict(self):
        """Convert clip to dictionary"""
        data = super().to_dict()
        data['status'] = self.status.value if self.status else None
        return data
