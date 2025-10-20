"""Health check controller."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.session import get_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the service is running and healthy"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic service information.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "0.1.0",
    }


@router.get(
    "/health/db",
    status_code=status.HTTP_200_OK,
    summary="Database health check",
    description="Check if database connection is healthy"
)
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """
    Database health check endpoint.
    
    Verifies database connectivity.
    """
    try:
        # Execute simple query to check database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
