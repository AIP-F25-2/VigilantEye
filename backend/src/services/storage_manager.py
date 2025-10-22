"""Storage management service with TTL and cleanup."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.storage import FileType, StorageFile, StorageStatus
from src.repositories.storage import StorageRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageManager:
    """Manage file storage with TTL and automatic cleanup."""

    def __init__(self, session: AsyncSession):
        """Initialize storage manager."""
        self.session = session
        self.storage_repository = StorageRepository(session)

    def calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def register_file(
        self,
        user_id: int,
        file_type: FileType,
        file_path: str,
        ttl_hours: int = 1,
        video_id: Optional[int] = None,
        processing_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        calculate_checksum: bool = False,
    ) -> StorageFile:
        """
        Register a file in storage tracking system.
        
        Args:
            user_id: User ID
            file_type: Type of file
            file_path: Path to file
            ttl_hours: Time to live in hours
            video_id: Optional video ID
            processing_id: Optional processing batch ID
            mime_type: MIME type
            metadata: Additional metadata
            calculate_checksum: Whether to calculate file checksum
            
        Returns:
            Created storage file record
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file info
        file_size = path.stat().st_size
        filename = path.name
        
        # Calculate checksum if requested
        checksum = None
        if calculate_checksum:
            try:
                checksum = self.calculate_checksum(file_path)
            except Exception as e:
                logger.warning(f"Failed to calculate checksum: {e}")
        
        # Convert metadata to JSON
        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata)
        
        # Create storage record
        storage_file = await self.storage_repository.create(
            user_id=user_id,
            file_type=file_type,
            filename=filename,
            file_path=str(path.absolute()),
            file_size=file_size,
            ttl_hours=ttl_hours,
            video_id=video_id,
            processing_id=processing_id,
            mime_type=mime_type,
            metadata=metadata_json,
            checksum=checksum,
        )
        
        await self.session.commit()
        
        logger.info(
            f"Registered file: {filename} ({file_type.value}) "
            f"TTL: {ttl_hours}h, Expires: {storage_file.expires_at}"
        )
        
        return storage_file

    async def register_batch(
        self,
        user_id: int,
        files: List[Dict],
        processing_id: str,
        ttl_hours: int = 1,
        video_id: Optional[int] = None,
    ) -> List[StorageFile]:
        """
        Register multiple files in batch.
        
        Args:
            user_id: User ID
            files: List of file dictionaries with type and path
            processing_id: Processing batch ID
            ttl_hours: Time to live in hours
            video_id: Optional video ID
            
        Returns:
            List of created storage file records
        """
        storage_files = []
        
        for file_info in files:
            try:
                storage_file = await self.register_file(
                    user_id=user_id,
                    file_type=file_info['type'],
                    file_path=file_info['path'],
                    ttl_hours=ttl_hours,
                    video_id=video_id,
                    processing_id=processing_id,
                    mime_type=file_info.get('mime_type'),
                    metadata=file_info.get('metadata'),
                )
                storage_files.append(storage_file)
            except Exception as e:
                logger.error(f"Failed to register file {file_info['path']}: {e}")
        
        logger.info(
            f"Registered {len(storage_files)}/{len(files)} files "
            f"for processing {processing_id}"
        )
        
        return storage_files

    async def cleanup_expired_files(self, limit: int = 100) -> Dict:
        """
        Clean up expired files from disk and database.
        
        Args:
            limit: Maximum number of files to clean up
            
        Returns:
            Cleanup statistics
        """
        logger.info(f"Starting cleanup of expired files (limit: {limit})")
        
        # Get expired files
        expired_files = await self.storage_repository.get_expired_files(limit)
        
        if not expired_files:
            logger.info("No expired files to clean up")
            return {
                'checked': 0,
                'deleted': 0,
                'failed': 0,
                'space_freed': 0
            }
        
        logger.info(f"Found {len(expired_files)} expired files")
        
        deleted_count = 0
        failed_count = 0
        space_freed = 0
        
        for storage_file in expired_files:
            try:
                # Delete file from disk
                file_path = Path(storage_file.file_path)
                
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    space_freed += file_size
                    logger.debug(f"Deleted file: {storage_file.filename}")
                else:
                    logger.warning(f"File not found: {storage_file.filename}")
                
                # Mark as deleted in database
                await self.storage_repository.mark_as_deleted(storage_file.id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete {storage_file.filename}: {e}")
                failed_count += 1
        
        await self.session.commit()
        
        result = {
            'checked': len(expired_files),
            'deleted': deleted_count,
            'failed': failed_count,
            'space_freed': space_freed,
            'space_freed_mb': round(space_freed / 1024 / 1024, 2)
        }
        
        logger.info(
            f"Cleanup completed: {deleted_count} deleted, {failed_count} failed, "
            f"{result['space_freed_mb']}MB freed"
        )
        
        return result

    async def extend_file_ttl(self, file_id: int, hours: int) -> StorageFile:
        """
        Extend TTL for a specific file.
        
        Args:
            file_id: Storage file ID
            hours: Hours to extend
            
        Returns:
            Updated storage file
        """
        storage_file = await self.storage_repository.extend_ttl(file_id, hours)
        await self.session.commit()
        
        logger.info(
            f"Extended TTL for {storage_file.filename} by {hours}h "
            f"(new expiry: {storage_file.expires_at})"
        )
        
        return storage_file

    async def extend_processing_ttl(self, processing_id: str, hours: int) -> int:
        """
        Extend TTL for all files in a processing batch.
        
        Args:
            processing_id: Processing batch ID
            hours: Hours to extend
            
        Returns:
            Number of files updated
        """
        files = await self.storage_repository.get_by_processing_id(processing_id)
        
        for file in files:
            await self.storage_repository.extend_ttl(file.id, hours)
        
        await self.session.commit()
        
        logger.info(
            f"Extended TTL for {len(files)} files in processing {processing_id} by {hours}h"
        )
        
        return len(files)

    async def get_storage_stats(self, user_id: Optional[int] = None) -> Dict:
        """
        Get storage statistics.
        
        Args:
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Storage statistics
        """
        stats = await self.storage_repository.get_storage_stats(user_id)
        
        # Calculate totals
        total_files = sum(stat['count'] for stat in stats.values())
        total_size = sum(stat['total_size'] for stat in stats.values())
        
        return {
            'by_type_and_status': stats,
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'total_size_gb': round(total_size / 1024 / 1024 / 1024, 2),
        }

    async def delete_processing_files(self, processing_id: str) -> Dict:
        """
        Delete all files for a processing batch.
        
        Args:
            processing_id: Processing batch ID
            
        Returns:
            Deletion statistics
        """
        files = await self.storage_repository.get_by_processing_id(processing_id)
        
        deleted_count = 0
        failed_count = 0
        space_freed = 0
        
        for storage_file in files:
            try:
                file_path = Path(storage_file.file_path)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    space_freed += file_size
                
                await self.storage_repository.mark_as_deleted(storage_file.id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete {storage_file.filename}: {e}")
                failed_count += 1
        
        await self.session.commit()
        
        return {
            'processing_id': processing_id,
            'total_files': len(files),
            'deleted': deleted_count,
            'failed': failed_count,
            'space_freed_mb': round(space_freed / 1024 / 1024, 2)
        }


async def get_storage_manager(session: AsyncSession) -> StorageManager:
    """Factory function to create storage manager."""
    return StorageManager(session)
