from app import db
from app.models.base import BaseModel
from sqlalchemy import JSON
import enum

class ProjectStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ProjectRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class Project(BaseModel):
    """Project model for organizing videos and recordings"""
    __tablename__ = 'projects'
    
    # Project details
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    
    # Project settings
    project_settings = db.Column(JSON, default=dict)
    storage_quota_bytes = db.Column(db.BigInteger, nullable=True)
    used_storage_bytes = db.Column(db.BigInteger, default=0)
    
    # Access control
    is_public = db.Column(db.Boolean, default=False)
    allow_guest_upload = db.Column(db.Boolean, default=False)
    
    # Project metadata
    tags = db.Column(JSON, default=list)
    category = db.Column(db.String(100), nullable=True)
    
    # Statistics
    total_videos = db.Column(db.Integer, default=0)
    total_recordings = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Float, default=0.0)  # in seconds
    
    # Relationships
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Related objects
    videos = db.relationship('Video', backref='project', lazy='dynamic')
    recordings = db.relationship('Recording', backref='project', lazy='dynamic')
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        """Convert project to dictionary"""
        data = super().to_dict()
        data['status'] = self.status.value if self.status else None
        return data

class ProjectMember(BaseModel):
    """Project membership model"""
    __tablename__ = 'project_members'
    
    # Membership details
    role = db.Column(db.Enum(ProjectRole), nullable=False)
    joined_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Permissions
    can_upload = db.Column(db.Boolean, default=True)
    can_edit = db.Column(db.Boolean, default=True)
    can_delete = db.Column(db.Boolean, default=False)
    can_invite = db.Column(db.Boolean, default=False)
    
    # Invitation details
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invitation_token = db.Column(db.String(100), nullable=True)
    invitation_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ensure unique user per project
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id'),)
    
    def __repr__(self):
        return f'<ProjectMember {self.user_id} in {self.project_id} as {self.role.value}>'
    
    def to_dict(self):
        """Convert project member to dictionary"""
        data = super().to_dict()
        data['role'] = self.role.value if self.role else None
        return data
