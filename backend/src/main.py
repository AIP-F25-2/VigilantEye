"""Application entry point."""

# CRITICAL: Import typing module BEFORE any cv2 imports to avoid cv2.typing conflict
# This must be done before any other imports that might trigger cv2 import
import sys
import typing  # Import stdlib typing first to prevent cv2.typing from being used
from typing import Any, Dict, List, Optional  # Pre-import common typing types

# Ensure stdlib typing is in sys.modules before cv2 can register its own
if 'typing' not in sys.modules or not hasattr(sys.modules['typing'], 'Any'):
    # Force reload if cv2.typing was already loaded
    import importlib
    if 'cv2.typing' in sys.modules:
        # Remove cv2.typing from sys.modules to force use of stdlib typing
        del sys.modules['cv2.typing']
    # Ensure stdlib typing is loaded
    importlib.reload(typing)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


from src.api import auth, health, video, ticket, model_cache, cleanup
from src.config import get_settings
from src.config.ai_config import AIConfig
from src.database import DatabaseSession
from src.middleware.error_handler import error_handler_middleware
from src.services.periodic_cleanup_service import start_cleanup_scheduler
from src.utils.logger import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    import asyncio
    
    # Startup
    logger.info("Starting application...")
    settings = get_settings()
    ai_config = AIConfig()
    
    # Store settings in app state
    app.state.settings = settings
    
    # Initialize database
    db = DatabaseSession()
    db.initialize()
    logger.info("Database initialized")
    
    # Start background services
    logger.info("Starting background services...")
    cleanup_task = None
    
    # Start cleanup scheduler if enabled
    if ai_config.cleanup_enabled:
        logger.info("Starting periodic cleanup scheduler...")
        cleanup_task = asyncio.create_task(start_cleanup_scheduler())
    else:
        logger.info("Periodic cleanup is disabled")
    
    logger.info(f"Application started - Environment: {settings.app_env}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop background services
    if cleanup_task:
        logger.info("Stopping cleanup scheduler...")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("Cleanup scheduler stopped")
    
    # Close database connection
    await db.close()
    logger.info("Database connection closed")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Enterprise Backend System with Authentication",
        docs_url="/api/docs" if settings.app_debug else None,
        redoc_url="/api/redoc" if settings.app_debug else None,
        lifespan=lifespan,
    )
    
    # Configure CORS - More permissive for development
    cors_origins = settings.cors_origins_list.copy() if settings.cors_origins_list else []
    
    # In development, allow all localhost ports
    if settings.is_development:
        # Add common development ports if not already included
        localhost_origins = [
            "http://localhost:3000",
            "http://localhost:5173",  # Vite default
            "http://localhost:5174",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:8080",
        ]
        # Merge with configured origins, avoiding duplicates
        for origin in localhost_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
        logger.info(f"CORS configured for development with origins: {cors_origins}")
    
    # Use wildcard for development if no specific origins configured
    # This allows any origin in development (less secure but easier for dev)
    if settings.is_development and not cors_origins:
        cors_origins = ["*"]
        logger.info("CORS configured to allow all origins in development")
    
    # Configure CORS middleware - must be added FIRST (before other middleware)
    # Use regex pattern to allow any localhost port in development
    if settings.is_development:
        # In development, use regex to allow any localhost port dynamically
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+",
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600,
        )
        logger.info("CORS configured with regex pattern for development (allows any localhost port)")
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=3600,
        )
    
    # Add custom middleware AFTER CORS
    app.middleware("http")(error_handler_middleware)
    
    # Add exception handler for FastAPI validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI request validation errors."""
        logger.warning(f"Validation error on {request.method} {request.url}: {exc.errors()}")
        origin = request.headers.get("origin", "*")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": exc.errors(),
                "code": "VALIDATION_ERROR",
            },
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
        )
    
    # Register routers
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(video.router, prefix="/api")
    app.include_router(ticket.router, prefix="/api")
    app.include_router(model_cache.router, prefix="/api/models")
    app.include_router(cleanup.router, prefix="/api")
    
    logger.info("Application configured successfully")
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
