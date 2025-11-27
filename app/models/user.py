
from app import db
from app.models.base import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import JSON
from datetime import datetime, timedelta, timezone

class User(BaseModel):
    """User model"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    roles = db.Column(JSON, default=list)  # List of user roles
    site_id = db.Column(db.String(100), default="default")  # Site identifier
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary excluding sensitive data"""
        data = super().to_dict()
        data.pop('password_hash', None)
        return data
    
    def get_identity(self):
        """Get user identity for JWT"""
        return {
            'id': self.id,
            'email': self.email,
            'roles': self.roles or [],
            'site_id': self.site_id
        }
    
    def generate_reset_token(self):
        """Generate a password reset token"""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        self.save()
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify if reset token is valid"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if self.reset_token != token:
            return False
        if datetime.now(timezone.utc) > self.reset_token_expires:
            return False
        return True
    
    def clear_reset_token(self):
        """Clear reset token after use"""
        self.reset_token = None
        self.reset_token_expires = None
        self.save()
