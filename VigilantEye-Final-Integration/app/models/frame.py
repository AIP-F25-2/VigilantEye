from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class FrameType(enum.Enum):
    SINGLE = "single"
    BATCH = "batch"
    AUTO = "auto"

class Frame(BaseModel):
    """Frame extraction model"""
    __tablename__ = 'frames'
    
    # Frame details
    frame_type = db.Column(db.Enum(FrameType), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    
    # Timing info
    offset_seconds = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=True)
    
    # Image properties
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=False)
    quality = db.Column(db.Integer, nullable=True)  # JPEG quality
    
    # Batch info (for batch frames)
    batch_id = db.Column(db.String(100), nullable=True)
    batch_index = db.Column(db.Integer, nullable=True)
    
    # Metadata
    frame_metadata = db.Column(JSON, default=dict)
    
    # Relationships
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    def __repr__(self):
        return f'<Frame {self.filename} at {self.offset_seconds}s>'
    
    def to_dict(self):
        """Convert frame to dictionary"""
        data = super().to_dict()
        data['frame_type'] = self.frame_type.value if self.frame_type else None
        return data

class FrameBatch(BaseModel):
    """Frame batch processing model"""
    __tablename__ = 'frame_batches'
    
    # Batch details
    batch_name = db.Column(db.String(255), nullable=False)
    folder_path = db.Column(db.String(500), nullable=False)
    
    # Processing parameters
    start_seconds = db.Column(db.Float, default=0.0)
    end_seconds = db.Column(db.Float, nullable=True)
    interval_seconds = db.Column(db.Float, nullable=False)
    max_frames = db.Column(db.Integer, nullable=True)
    
    # Results
    total_frames = db.Column(db.Integer, default=0)
    processed_frames = db.Column(db.Integer, default=0)
    zip_path = db.Column(db.String(500), nullable=True)
    
    # Status
    is_completed = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Metadata
    batch_settings = db.Column(JSON, default=dict)
    
    # Relationships
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    # Related frames
    frames = db.relationship('Frame', backref='batch', lazy='dynamic')
    
    def __repr__(self):
        return f'<FrameBatch {self.batch_name}>'
