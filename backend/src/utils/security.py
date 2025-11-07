"""
Security utilities and middleware for VigilantEye.
"""

import time
import hashlib
import secrets
from typing import Optional, Dict, Any
from functools import wraps
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging
from jose import JWTError, jwt
from passlib.context import CryptContext
from src.config import get_settings
from src.services.local_cache import get_cache
from src.utils.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting storage (Local Cache)
cache = get_cache()

class SecurityManager:
    """Centralized security management."""
    
    def __init__(self):
        self.failed_attempts = {}
        self.blocked_ips = set()
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data with salt."""
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()
    
    def is_rate_limited(self, identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if identifier is rate limited."""
        key = f"rate_limit:{identifier}"
        current = cache.get(key)
        
        if current is None:
            cache.set(key, 1, ttl=window)
            return False
        
        current_count = int(current) + 1
        cache.set(key, current_count, ttl=window)
        
        return current_count > limit
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events for monitoring."""
        logger.warning(f"Security Event: {event_type}", extra={
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        })

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Rate limiting decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            user_agent = request.headers.get("user-agent", "")
            identifier = f"{client_ip}:{hashlib.md5(user_agent.encode()).hexdigest()}"
            
            if SecurityManager().is_rate_limited(identifier, max_requests, window_seconds):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_permissions(required_permissions: list):
    """Decorator to require specific permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Implementation would check user permissions
            # This is a placeholder for actual permission checking
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class SecurityHeaders:
    """Add security headers to responses."""
    
    @staticmethod
    def add_security_headers(response):
        """Add comprehensive security headers."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

def validate_file_upload(file_content: bytes, allowed_types: list, max_size: int) -> bool:
    """Validate uploaded file for security."""
    if len(file_content) > max_size:
        return False
    
    # Check file signature (magic bytes)
    file_signatures = {
        'video/mp4': [b'\x00\x00\x00\x18ftypmp42', b'\x00\x00\x00\x20ftypisom'],
        'image/jpeg': [b'\xff\xd8\xff'],
        'image/png': [b'\x89PNG\r\n\x1a\n'],
    }
    
    for file_type, signatures in file_signatures.items():
        if file_type in allowed_types:
            for signature in signatures:
                if file_content.startswith(signature):
                    return True
    
    return False

class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks."""
    
    @staticmethod
    def sanitize_string(input_str: str) -> str:
        """Sanitize string input."""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        for char in dangerous_chars:
            input_str = input_str.replace(char, '')
        return input_str.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for security."""
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(pattern in filename for pattern in dangerous_patterns)


# JWT Token Functions

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Dictionary containing token payload (sub, email, role, etc.)
        
    Returns:
        Encoded JWT access token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Dictionary containing token payload (typically just sub)
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        UnauthorizedException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        raise UnauthorizedException(
            message="Invalid token",
            detail="Token is invalid or expired"
        )


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
    """
    Verify token type matches expected type.
    
    Args:
        payload: Decoded token payload
        expected_type: Expected token type ("access" or "refresh")
        
    Raises:
        UnauthorizedException: If token type doesn't match
    """
    token_type = payload.get("type")
    if token_type != expected_type:
        raise UnauthorizedException(
            message="Invalid token type",
            detail=f"Expected {expected_type} token, got {token_type}"
        )


# Password Functions

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)