"""Cleanup management API endpoints."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import AdminUser, CurrentUser
from src.database.session import get_db
from src.services.periodic_cleanup_service import get_cleanup_service, run_manual_cleanup
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Global variable to track cleanup status
_cleanup_status = {
    "last_run": None,
    "next_run": None,
    "is_running": False,
    "total_runs": 0,
    "last_cleanup_stats": {}
}


@router.get(
    "/cleanup/status",
    summary="Get cleanup status",
    description="Get current cleanup status and next run time"
)
async def get_cleanup_status(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get cleanup status."""
    try:
        cleanup_service = get_cleanup_service()
        
        # Calculate next run time
        if _cleanup_status["last_run"]:
            next_run = _cleanup_status["last_run"] + timedelta(hours=cleanup_service.cleanup_interval_hours)
        else:
            next_run = datetime.utcnow() + timedelta(hours=cleanup_service.cleanup_interval_hours)
        
        _cleanup_status["next_run"] = next_run
        
        status_info = {
            "cleanup_enabled": cleanup_service.cleanup_enabled,
            "is_running": _cleanup_status["is_running"],
            "last_run": _cleanup_status["last_run"].isoformat() if _cleanup_status["last_run"] else None,
            "next_run": next_run.isoformat(),
            "total_runs": _cleanup_status["total_runs"],
            "last_cleanup_stats": _cleanup_status["last_cleanup_stats"],
            "configuration": {
                "cleanup_interval_hours": cleanup_service.cleanup_interval_hours,
                "person_data_retention_days": cleanup_service.person_data_retention_days,
                "embedding_data_retention_days": cleanup_service.embedding_data_retention_days,
                "media_retention_days": cleanup_service.media_retention_days
            }
        }
        
        return {"success": True, "data": status_info}
        
    except Exception as e:
        logger.error(f"Failed to get cleanup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cleanup status"
        )


@router.get(
    "/cleanup/stats",
    summary="Get cleanup statistics",
    description="Get statistics about cleanup operations (Admin only)"
)
async def get_cleanup_stats(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get cleanup statistics."""
    try:
        cleanup_service = get_cleanup_service()
        
        stats = {
            "cleanup_enabled": cleanup_service.cleanup_enabled,
            "cleanup_interval_hours": cleanup_service.cleanup_interval_hours,
            "person_data_retention_days": cleanup_service.person_data_retention_days,
            "embedding_data_retention_days": cleanup_service.embedding_data_retention_days,
            "media_retention_days": cleanup_service.media_retention_days,
            "total_cleanup_runs": _cleanup_status["total_runs"],
            "last_run": _cleanup_status["last_run"].isoformat() if _cleanup_status["last_run"] else None,
            "next_run": _cleanup_status["next_run"].isoformat() if _cleanup_status["next_run"] else None,
            "last_cleanup_results": _cleanup_status["last_cleanup_stats"]
        }
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        logger.error(f"Failed to get cleanup stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cleanup statistics"
        )


@router.post(
    "/cleanup/run",
    summary="Run manual cleanup",
    description="Run manual cleanup with optional custom retention period (Admin only)"
)
async def run_cleanup(
    days: Optional[int] = None,
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Run manual cleanup."""
    try:
        if _cleanup_status["is_running"]:
            return {
                "success": False,
                "message": "Cleanup is already running",
                "data": {"is_running": True}
            }
        
        _cleanup_status["is_running"] = True
        
        try:
            result = await run_manual_cleanup(days)
            
            # Update status
            _cleanup_status["last_run"] = datetime.utcnow()
            _cleanup_status["total_runs"] += 1
            _cleanup_status["last_cleanup_stats"] = result
            
            logger.info(f"Manual cleanup completed: {result}")
            
            return {
                "success": True,
                "message": f"Manual cleanup completed successfully",
                "data": result
            }
            
        finally:
            _cleanup_status["is_running"] = False
        
    except Exception as e:
        _cleanup_status["is_running"] = False
        logger.error(f"Failed to run manual cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run cleanup: {str(e)}"
        )


@router.post(
    "/cleanup/test",
    summary="Test cleanup (dry run)",
    description="Test cleanup without actually deleting data (Admin only)"
)
async def test_cleanup(
    days: Optional[int] = None,
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Test cleanup without actually deleting data."""
    try:
        cleanup_service = get_cleanup_service()
        
        # Simulate what would be cleaned
        retention_days = days or cleanup_service.person_data_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # This would be a dry run implementation
        test_result = {
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "would_clean": {
                "person_records": f"Records older than {retention_days} days",
                "embedding_records": f"Embeddings older than {retention_days} days", 
                "media_files": f"Media files older than {retention_days} days",
                "orphaned_files": f"Orphaned files older than {retention_days} days"
            },
            "note": "This is a dry run - no data was actually deleted"
        }
        
        return {
            "success": True,
            "message": "Cleanup test completed",
            "data": test_result
        }
        
    except Exception as e:
        logger.error(f"Failed to test cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test cleanup: {str(e)}"
        )


@router.get(
    "/cleanup/config",
    summary="Get cleanup configuration",
    description="Get current cleanup configuration (Admin only)"
)
async def get_cleanup_config(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get cleanup configuration."""
    try:
        cleanup_service = get_cleanup_service()
        
        config = {
            "cleanup_enabled": cleanup_service.cleanup_enabled,
            "cleanup_interval_hours": cleanup_service.cleanup_interval_hours,
            "person_data_retention_days": cleanup_service.person_data_retention_days,
            "embedding_data_retention_days": cleanup_service.embedding_data_retention_days,
            "media_retention_days": cleanup_service.media_retention_days,
            "automatic_cleanup": {
                "enabled": cleanup_service.cleanup_enabled,
                "interval_hours": cleanup_service.cleanup_interval_hours,
                "description": "Automatic cleanup runs in the background at specified intervals"
            }
        }
        
        return {"success": True, "data": config}
        
    except Exception as e:
        logger.error(f"Failed to get cleanup config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cleanup configuration"
        )


def update_cleanup_status(last_run: datetime, stats: Dict):
    """Update cleanup status (called by cleanup service)."""
    global _cleanup_status
    _cleanup_status["last_run"] = last_run
    _cleanup_status["total_runs"] += 1
    _cleanup_status["last_cleanup_stats"] = stats
