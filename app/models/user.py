
from app import db
from app.models.base import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import JSON

class User(BaseModel):
    """User model"""
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    roles = db.Column(JSON, default=list)  # List of user roles
    site_id = db.Column(db.String(100), default="default")  # Site identifier
    
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
