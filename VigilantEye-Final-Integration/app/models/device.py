from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class DeviceType(enum.Enum):
    WEBCAM = "webcam"
    SCREEN = "screen"
    RTSP = "rtsp"
    AUDIO = "audio"
    FILE = "file"

class DeviceStatus(enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

class Device(BaseModel):
    """Device model for recording sources"""
    __tablename__ = 'devices'
    
    # Device identification
    device_id = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    device_type = db.Column(db.Enum(DeviceType), nullable=False)
    
    # Device properties
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.AVAILABLE)
    is_default = db.Column(db.Boolean, default=False)
    
    # Technical details
    driver = db.Column(db.String(100), nullable=True)  # DirectShow, V4L2, etc.
    capabilities = db.Column(JSON, default=dict)
    supported_formats = db.Column(JSON, default=list)
    supported_resolutions = db.Column(JSON, default=list)
    supported_framerates = db.Column(JSON, default=list)
    
    # Connection info
    connection_string = db.Column(db.String(500), nullable=True)
    rtsp_url = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    port = db.Column(db.Integer, nullable=True)
    
    # Device metadata
    manufacturer = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    version = db.Column(db.String(50), nullable=True)
    serial_number = db.Column(db.String(100), nullable=True)
    
    # Usage tracking
    last_used_at = db.Column(db.DateTime, nullable=True)
    usage_count = db.Column(db.Integer, default=0)
    total_recording_time = db.Column(db.Float, default=0.0)  # in seconds
    
    # Settings and configuration
    default_settings = db.Column(JSON, default=dict)
    current_settings = db.Column(JSON, default=dict)
    
    # Error tracking
    last_error = db.Column(db.Text, nullable=True)
    error_count = db.Column(db.Integer, default=0)
    last_error_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def __repr__(self):
        return f'<Device {self.name} ({self.device_type.value})>'
    
    def to_dict(self):
        """Convert device to dictionary"""
        data = super().to_dict()
        data['device_type'] = self.device_type.value if self.device_type else None
        data['status'] = self.status.value if self.status else None
        return data
