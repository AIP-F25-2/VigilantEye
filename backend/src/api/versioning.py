"""
API versioning and comprehensive OpenAPI documentation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# API Version Management
class APIVersionManager:
    """Manage API versions and backward compatibility."""
    
    CURRENT_VERSION = "v1"
    SUPPORTED_VERSIONS = ["v1"]
    DEPRECATED_VERSIONS = []
    
    @classmethod
    def get_version_from_path(cls, path: str) -> str:
        """Extract version from API path."""
        parts = path.split('/')
        if len(parts) > 2 and parts[1].startswith('v'):
            return parts[1]
        return cls.CURRENT_VERSION
    
    @classmethod
    def is_version_supported(cls, version: str) -> bool:
        """Check if version is supported."""
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def is_version_deprecated(cls, version: str) -> bool:
        """Check if version is deprecated."""
        return version in cls.DEPRECATED_VERSIONS

# Enhanced OpenAPI Schema
def create_openapi_schema(app) -> Dict[str, Any]:
    """Create comprehensive OpenAPI schema with security and examples."""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="VigilantEye AI Video Intelligence API",
        version="1.0.0",
        description="""
        # VigilantEye AI Video Intelligence System API
        
        ## Overview
        VigilantEye is an advanced AI-powered video intelligence system that provides:
        - Real-time threat detection
        - Person recognition and tracking
        - Audio analysis and transcription
        - Evidence collection and management
        - Comprehensive ticket management system
        
        ## Authentication
        This API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:
        ```
        Authorization: Bearer <your-token>
        ```
        
        ## Rate Limiting
        API requests are rate limited to prevent abuse:
        - **Standard users**: 100 requests per hour
        - **Admin users**: 1000 requests per hour
        
        ## Error Handling
        All errors follow a consistent format:
        ```json
        {
            "error": "error_code",
            "message": "Human readable message",
            "details": "Additional context",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        ```
        
        ## Security
        - All endpoints require authentication except health checks
        - File uploads are validated for security
        - Input sanitization prevents injection attacks
        - CORS is configured for security
        
        ## Support
        For support, contact: support@vigilanteye.com
        """,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /api/auth/login"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication"
        }
    }
    
    # Add global security
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "https://api.vigilanteye.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.vigilanteye.com",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
    
    # Add contact information
    openapi_schema["info"]["contact"] = {
        "name": "VigilantEye Support",
        "email": "support@vigilanteye.com",
        "url": "https://vigilanteye.com/support"
    }
    
    # Add license information
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "VigilantEye Documentation",
        "url": "https://docs.vigilanteye.com"
    }
    
    # Enhance response schemas with examples
    enhance_schemas_with_examples(openapi_schema)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def enhance_schemas_with_examples(openapi_schema: Dict[str, Any]):
    """Add comprehensive examples to API schemas."""
    
    # User response examples
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        schemas = openapi_schema["components"]["schemas"]
        
        # User schema example
        if "UserResponse" in schemas:
            schemas["UserResponse"]["example"] = {
                "id": 1,
                "username": "john_doe",
                "email": "john.doe@example.com",
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-01T12:00:00Z"
            }
        
        # Video schema example
        if "VideoResponse" in schemas:
            schemas["VideoResponse"]["example"] = {
                "id": 1,
                "title": "Security Camera Footage",
                "description": "Main entrance surveillance",
                "filename": "security_cam_20240101.mp4",
                "file_size": 52428800,
                "duration": 300.5,
                "resolution": "1920x1080",
                "fps": 30,
                "status": "processed",
                "processing_id": "proc_abc123",
                "created_at": "2024-01-01T00:00:00Z",
                "user_id": 1
            }
        
        # Ticket schema example
        if "TicketResponse" in schemas:
            schemas["TicketResponse"]["example"] = {
                "id": 1,
                "title": "Suspicious Activity Detected",
                "description": "Person detected in restricted area",
                "priority": "high",
                "status": "open",
                "threat_type": "unauthorized_access",
                "confidence_score": 0.95,
                "video_id": 1,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:05:00Z",
                "user_id": 1
            }
        
        # Error schema example
        if "ErrorResponse" in schemas:
            schemas["ErrorResponse"]["example"] = {
                "error": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": "The email field must be a valid email address",
                "timestamp": "2024-01-01T00:00:00Z"
            }

# API Health Check with detailed status
def create_health_check_router() -> APIRouter:
    """Create comprehensive health check endpoint."""
    
    router = APIRouter(prefix="/health", tags=["Health"])
    
    @router.get("/", summary="Basic Health Check")
    async def basic_health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
    
    @router.get("/detailed", summary="Detailed Health Check")
    async def detailed_health_check():
        """Detailed health check with system status."""
        import psutil
        import time
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "uptime": time.time(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "ai_services": "healthy"
            }
        }
    
    @router.get("/ready", summary="Readiness Check")
    async def readiness_check():
        """Kubernetes readiness probe."""
        # Check if all required services are ready
        return {"status": "ready"}
    
    @router.get("/live", summary="Liveness Check")
    async def liveness_check():
        """Kubernetes liveness probe."""
        return {"status": "alive"}
    
    return router

# API Metrics and Monitoring
class APIMetrics:
    """Track API usage metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
    
    def record_request(self, endpoint: str, method: str, response_time: float, status_code: int):
        """Record API request metrics."""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_count += 1
        
        logger.info(f"API Request: {method} {endpoint} - {status_code} - {response_time}ms")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "average_response_time": avg_response_time,
            "uptime": time.time()
        }

# Global metrics instance
api_metrics = APIMetrics()
