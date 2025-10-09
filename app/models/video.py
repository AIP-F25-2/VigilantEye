from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
from datetime import datetime
import enum

class VideoStatus(enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class Video(BaseModel):
    """Video model for storing video metadata"""
    __tablename__ = 'videos'
    
    # Basic info
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    
    # File properties
    size_bytes = db.Column(db.BigInteger, nullable=False)
    size_human = db.Column(db.String(50), nullable=False)
    checksum = db.Column(db.String(64), nullable=False, unique=True)
    mimetype = db.Column(db.String(100), nullable=False)
    
    # Video properties
    duration_seconds = db.Column(db.Float, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    fps = db.Column(db.Float, nullable=True)
    bitrate = db.Column(db.Integer, nullable=True)
    codec = db.Column(db.String(50), nullable=True)
    
    # Status and metadata
    status = db.Column(db.Enum(VideoStatus), default=VideoStatus.READY)
    video_metadata = db.Column(JSON, default=dict)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    # Related objects
    recordings = db.relationship('Recording', backref='video', lazy='dynamic')
    frames = db.relationship('Frame', backref='video', lazy='dynamic')
    clips = db.relationship('Clip', backref='video', lazy='dynamic')
    segments = db.relationship('Segment', backref='video', lazy='dynamic')
    view_events = db.relationship('ViewEvent', backref='video', lazy='dynamic')
    
    def __repr__(self):
        return f'<Video {self.filename}>'
    
    def to_dict(self):
        """Convert video to dictionary"""
        data = super().to_dict()
        data['status'] = self.status.value if self.status else None
        return data

class VideoMetadata(BaseModel):
    """Additional metadata for videos"""
    __tablename__ = 'video_metadata'
    
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=False)
    data_type = db.Column(db.String(20), default='string')  # string, int, float, json, bool
    
    # Ensure unique key per video
    __table_args__ = (db.UniqueConstraint('video_id', 'key'),)
    
    def __repr__(self):
        return f'<VideoMetadata {self.key}={self.value}>'
