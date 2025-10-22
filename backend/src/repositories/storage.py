"""Storage repository."""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.storage import FileType, StorageFile, StorageStatus


class StorageRepository:
    """Repository for StorageFile model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        user_id: int,
        file_type: FileType,
        filename: str,
        file_path: str,
        file_size: int,
        ttl_hours: int = 1,
        video_id: Optional[int] = None,
        processing_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[str] = None,
        checksum: Optional[str] = None,
    ) -> StorageFile:
        """
        Create a new storage file record.
        
        Args:
            user_id: User ID
            file_type: Type of file
            filename: File name
            file_path: Full file path
            file_size: File size in bytes
            ttl_hours: Time to live in hours
            video_id: Optional video ID
            processing_id: Optional processing ID
            mime_type: MIME type
            metadata: JSON metadata
            checksum: File checksum
            
        Returns:
            Created storage file instance
        """
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        storage_file = StorageFile(
            user_id=user_id,
            video_id=video_id,
            processing_id=processing_id,
            file_type=file_type,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            metadata=metadata,
            ttl_hours=ttl_hours,
            expires_at=expires_at,
            status=StorageStatus.ACTIVE,
            checksum=checksum,
        )
        
        self.session.add(storage_file)
        await self.session.flush()
        await self.session.refresh(storage_file)
        return storage_file

    async def get_by_id(self, file_id: int) -> Optional[StorageFile]:
        """Get storage file by ID."""
        result = await self.session.execute(
            select(StorageFile).where(StorageFile.id == file_id)
        )
        return result.scalar_one_or_none()

    async def get_expired_files(self, limit: int = 100) -> List[StorageFile]:
        """
        Get expired files that need deletion.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of expired storage files
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            select(StorageFile)
            .where(
                StorageFile.expires_at <= now,
                StorageFile.status.in_([StorageStatus.ACTIVE, StorageStatus.EXPIRED])
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_processing_id(self, processing_id: str) -> List[StorageFile]:
        """Get all files for a processing batch."""
        result = await self.session.execute(
            select(StorageFile).where(StorageFile.processing_id == processing_id)
        )
        return list(result.scalars().all())

    async def get_by_video_id(self, video_id: int) -> List[StorageFile]:
        """Get all files for a video."""
        result = await self.session.execute(
            select(StorageFile).where(StorageFile.video_id == video_id)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: int,
        file_type: Optional[FileType] = None,
        status: Optional[StorageStatus] = None,
    ) -> List[StorageFile]:
        """Get files for a user with optional filters."""
        query = select(StorageFile).where(StorageFile.user_id == user_id)
        
        if file_type:
            query = query.where(StorageFile.file_type == file_type)
        
        if status:
            query = query.where(StorageFile.status == status)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_expired(self, file_id: int) -> Optional[StorageFile]:
        """Mark file as expired."""
        storage_file = await self.get_by_id(file_id)
        if storage_file:
            storage_file.status = StorageStatus.EXPIRED
            await self.session.flush()
            await self.session.refresh(storage_file)
        return storage_file

    async def mark_as_deleted(self, file_id: int) -> Optional[StorageFile]:
        """Mark file as deleted."""
        storage_file = await self.get_by_id(file_id)
        if storage_file:
            storage_file.status = StorageStatus.DELETED
            storage_file.deleted_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(storage_file)
        return storage_file

    async def extend_ttl(self, file_id: int, hours: int) -> Optional[StorageFile]:
        """Extend TTL for a file."""
        storage_file = await self.get_by_id(file_id)
        if storage_file:
            storage_file.extend_ttl(hours)
            await self.session.flush()
            await self.session.refresh(storage_file)
        return storage_file

    async def get_storage_stats(self, user_id: Optional[int] = None) -> dict:
        """Get storage statistics."""
        query = select(
            StorageFile.file_type,
            StorageFile.status,
            func.count(StorageFile.id).label('count'),
            func.sum(StorageFile.file_size).label('total_size')
        ).group_by(StorageFile.file_type, StorageFile.status)
        
        if user_id:
            query = query.where(StorageFile.user_id == user_id)
        
        result = await self.session.execute(query)
        
        stats = {}
        for row in result:
            key = f"{row.file_type.value}_{row.status.value}"
            stats[key] = {
                'count': row.count,
                'total_size': row.total_size or 0
            }
        
        return stats

    async def delete_record(self, file_id: int) -> bool:
        """Delete storage file record from database."""
        storage_file = await self.get_by_id(file_id)
        if storage_file:
            await self.session.delete(storage_file)
            await self.session.flush()
            return True
        return False
