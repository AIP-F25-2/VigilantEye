from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class RecordingMode(enum.Enum):
    SCREEN = "screen"
    RTSP = "rtsp"
    WEBCAM = "webcam"
    FILE = "file"

class RecordingStatus(enum.Enum):
    STARTING = "starting"
    RECORDING = "recording"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Recording(BaseModel):
    """Recording session model"""
    __tablename__ = 'recordings'
    
    # Recording details
    mode = db.Column(db.Enum(RecordingMode), nullable=False)
    source = db.Column(db.String(500), nullable=True)  # RTSP URL, device name, etc.
    status = db.Column(db.Enum(RecordingStatus), default=RecordingStatus.STARTING)
    
    # Recording parameters
    fps = db.Column(db.Integer, default=30)
    duration_seconds = db.Column(db.Float, nullable=True)
    max_duration_seconds = db.Column(db.Float, nullable=True)
    
    # File paths
    output_path = db.Column(db.String(500), nullable=True)
    log_path = db.Column(db.String(500), nullable=True)
    
    # Process info
    process_id = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    recording_settings = db.Column(JSON, default=dict)
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    
    def __repr__(self):
        return f'<Recording {self.mode.value} - {self.status.value}>'
    
    def to_dict(self):
        """Convert recording to dictionary"""
        data = super().to_dict()
        data['mode'] = self.mode.value if self.mode else None
        data['status'] = self.status.value if self.status else None
        return data

class RecordingSession(BaseModel):
    """Recording session tracking"""
    __tablename__ = 'recording_sessions'
    
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Session info
    name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Session timing
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Session data
    total_recordings = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Float, default=0.0)  # in seconds
    session_settings = db.Column(JSON, default=dict)
    
    # Relationships
    recordings = db.relationship('Recording', backref='session', lazy='dynamic')
    
    def __repr__(self):
        return f'<RecordingSession {self.session_id}>'
