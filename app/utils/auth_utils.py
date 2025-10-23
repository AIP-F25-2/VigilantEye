from app import db
from app.models.user import User
from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import timedelta

# Simple in-memory token blacklist (for demo)
REVOKED: set = set()

def create_user(email, password, roles=None, site_id="default", username=None):
    """Create a new user"""
    if roles is None:
        roles = ["operator"]
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        raise ValueError("User with this email already exists")
    
    # Generate username from email if not provided
    if not username:
        username = email.split('@')[0]
    
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        raise ValueError("Username already exists")
    
    # Create new user
    user = User(
        email=email,
        username=username,
        roles=roles,
        site_id=site_id
    )
    user.set_password(password)
    
    try:
        user.save()
        return user.get_identity()
    except Exception as e:
        raise ValueError(f"Failed to create user: {str(e)}")

def verify_password(email, password):
    """Verify user password and return user identity"""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return None
    
    if not user.is_active:
        return None
    
    return user.get_identity()

def revoke_token(jti):
    """Revoke a token by adding it to blacklist"""
    REVOKED.add(jti)

def is_token_revoked(jti):
    """Check if token is revoked"""
    return jti in REVOKED

def create_tokens(identity):
    """Create access and refresh tokens for user identity"""
    access_token = create_access_token(
        identity=identity, 
        expires_delta=timedelta(hours=2)
    )
    refresh_token = create_refresh_token(
        identity=identity, 
        expires_delta=timedelta(days=14)
    )
    return access_token, refresh_token
