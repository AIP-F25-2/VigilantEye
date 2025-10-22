"""Storage management controller."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.models.storage import FileType, StorageStatus
from src.dto.base import BaseDTO
from src.services.storage_manager import StorageManager
from src.utils.logger import get_logger

from .dependencies import CurrentUser, AdminUser

router = APIRouter(prefix="/storage", tags=["Storage Management"])
logger = get_logger(__name__)


class StorageStatsResponse(BaseDTO):
    """Storage statistics response."""
    by_type_and_status: dict
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    total_size_gb: float


class CleanupResponse(BaseDTO):
    """Cleanup response."""
    checked: int
    deleted: int
    failed: int
    space_freed: int
    space_freed_mb: float


@router.get(
    "/stats",
    response_model=StorageStatsResponse,
    summary="Get storage statistics",
    description="Get storage usage statistics for current user"
)
async def get_storage_stats(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get storage statistics for current user."""
    storage_manager = StorageManager(db)
    stats = await storage_manager.get_storage_stats(user_id=current_user.id)
    return StorageStatsResponse(**stats)


@router.get(
    "/stats/all",
    response_model=StorageStatsResponse,
    summary="Get all storage statistics",
    description="Get storage usage statistics for all users (Admin only)"
)
async def get_all_storage_stats(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get storage statistics for all users (Admin only)."""
    storage_manager = StorageManager(db)
    stats = await storage_manager.get_storage_stats()
    return StorageStatsResponse(**stats)


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    summary="Trigger storage cleanup",
    description="Manually trigger cleanup of expired files (Admin only)"
)
async def trigger_cleanup(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Manually trigger storage cleanup."""
    storage_manager = StorageManager(db)
    result = await storage_manager.cleanup_expired_files(limit=limit)
    return CleanupResponse(**result)


@router.post(
    "/file/{file_id}/extend",
    summary="Extend file TTL",
    description="Extend time-to-live for a specific file"
)
async def extend_file_ttl(
    file_id: int,
    hours: int = Query(..., ge=1, le=168),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Extend TTL for a specific file."""
    storage_manager = StorageManager(db)
    
    try:
        storage_file = await storage_manager.extend_file_ttl(file_id, hours)
        
        # Check ownership
        if storage_file.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this file"
            )
        
        return {
            "file_id": file_id,
            "new_expires_at": storage_file.expires_at.isoformat(),
            "message": f"TTL extended by {hours} hours"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/processing/{processing_id}/extend",
    summary="Extend processing TTL",
    description="Extend TTL for all files in a processing batch"
)
async def extend_processing_ttl(
    processing_id: str,
    hours: int = Query(..., ge=1, le=168),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Extend TTL for all files in a processing batch."""
    storage_manager = StorageManager(db)
    
    # Note: Add ownership check by verifying processing_id belongs to user
    
    count = await storage_manager.extend_processing_ttl(processing_id, hours)
    
    return {
        "processing_id": processing_id,
        "files_updated": count,
        "message": f"TTL extended by {hours} hours for {count} files"
    }


@router.delete(
    "/processing/{processing_id}",
    summary="Delete processing files",
    description="Delete all files for a processing batch"
)
async def delete_processing_files(
    processing_id: str,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete all files for a processing batch."""
    storage_manager = StorageManager(db)
    
    # Note: Add ownership check
    
    result = await storage_manager.delete_processing_files(processing_id)
    
    return result
