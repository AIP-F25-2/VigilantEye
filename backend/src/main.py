"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from src.api import auth, health, video, ticket, model_cache
from src.config import get_settings
from src.database import DatabaseSession
from src.middleware.error_handler import error_handler_middleware
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
    # Startup
    logger.info("Starting application...")
    settings = get_settings()
    
    # Store settings in app state
    app.state.settings = settings
    
    # Initialize database
    db = DatabaseSession()
    db.initialize()
    logger.info("Database initialized")
    
    logger.info(f"Application started - Environment: {settings.app_env}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
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
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.middleware("http")(error_handler_middleware)
    
    # Register routers
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(video.router, prefix="/api")
app.include_router(ticket.router, prefix="/api")
app.include_router(model_cache.router, prefix="/api/models")
    
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
