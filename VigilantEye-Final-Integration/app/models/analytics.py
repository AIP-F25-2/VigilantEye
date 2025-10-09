from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class EventType(enum.Enum):
    VIEW = "view"
    DOWNLOAD = "download"
    STREAM = "stream"
    UPLOAD = "upload"
    RECORD = "record"
    CLIP = "clip"
    FRAME = "frame"
    DELETE = "delete"
    SHARE = "share"

class Analytics(BaseModel):
    """Analytics tracking model"""
    __tablename__ = 'analytics'
    
    # Event details
    event_type = db.Column(db.Enum(EventType), nullable=False)
    event_name = db.Column(db.String(100), nullable=False)
    
    # Resource being tracked
    resource_type = db.Column(db.String(50), nullable=False)  # video, recording, clip, etc.
    resource_id = db.Column(db.String(100), nullable=False)
    
    # User and session info
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Event data
    analytics_data = db.Column(JSON, default=dict)
    duration_seconds = db.Column(db.Float, nullable=True)
    
    # Geographic info
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(50), nullable=True)
    
    # Device info
    device_type = db.Column(db.String(50), nullable=True)  # desktop, mobile, tablet
    browser = db.Column(db.String(100), nullable=True)
    os = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<Analytics {self.event_type.value} - {self.event_name}>'
    
    def to_dict(self):
        """Convert analytics to dictionary"""
        data = super().to_dict()
        data['event_type'] = self.event_type.value if self.event_type else None
        return data

class ViewEvent(BaseModel):
    """Detailed view event tracking"""
    __tablename__ = 'view_events'
    
    # View details
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    
    # View timing
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    
    # View progress
    start_position = db.Column(db.Float, default=0.0)  # where they started watching
    end_position = db.Column(db.Float, nullable=True)  # where they stopped
    max_position = db.Column(db.Float, default=0.0)  # furthest they watched
    completion_percentage = db.Column(db.Float, default=0.0)
    
    # Quality and performance
    quality_level = db.Column(db.String(20), nullable=True)  # 720p, 1080p, etc.
    buffering_events = db.Column(db.Integer, default=0)
    total_buffering_time = db.Column(db.Float, default=0.0)
    
    # User interaction
    pause_count = db.Column(db.Integer, default=0)
    seek_count = db.Column(db.Integer, default=0)
    fullscreen_entered = db.Column(db.Boolean, default=False)
    
    # Technical details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    
    def __repr__(self):
        return f'<ViewEvent video:{self.video_id} duration:{self.duration_seconds}s>'
    
    def to_dict(self):
        """Convert view event to dictionary"""
        return super().to_dict()
