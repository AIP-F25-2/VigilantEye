"""Periodic cleanup service for person and embedding data."""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.session import get_db
from src.models.person_embeddings import PersonEmbedding, PersonAppearance, PersonMatch
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class PeriodicCleanupService:
    """Service for periodic cleanup of person and embedding data."""
    
    def __init__(self):
        """Initialize cleanup service."""
        self.cleanup_enabled = getattr(settings, 'cleanup_enabled', True)
        self.cleanup_interval_hours = getattr(settings, 'cleanup_interval_hours', 24)
        self.person_data_retention_days = getattr(settings, 'person_data_retention_days', 30)
        self.embedding_data_retention_days = getattr(settings, 'embedding_data_retention_days', 90)
        self.media_retention_days = getattr(settings, 'media_retention_days', 60)
        
        logger.info(f"Periodic cleanup service initialized:")
        logger.info(f"  - Cleanup enabled: {self.cleanup_enabled}")
        logger.info(f"  - Cleanup interval: {self.cleanup_interval_hours} hours")
        logger.info(f"  - Person data retention: {self.person_data_retention_days} days")
        logger.info(f"  - Embedding data retention: {self.embedding_data_retention_days} days")
        logger.info(f"  - Media retention: {self.media_retention_days} days")
    
    async def start_cleanup_scheduler(self):
        """Start the periodic cleanup scheduler."""
        if not self.cleanup_enabled:
            logger.info("Periodic cleanup is disabled")
            return
        
        logger.info("Starting periodic cleanup scheduler...")
        
        while True:
            try:
                await self.run_cleanup()
                await asyncio.sleep(self.cleanup_interval_hours * 3600)  # Convert hours to seconds
            except Exception as e:
                logger.error(f"Cleanup scheduler error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def run_cleanup(self):
        """Run the cleanup process."""
        logger.info("Starting periodic cleanup...")
        
        try:
            # Get database session
            async for db in get_db():
                # Clean person data
                person_cleaned = await self._cleanup_person_data(db)
                
                # Clean embedding data
                embedding_cleaned = await self._cleanup_embedding_data(db)
                
                # Clean media files
                media_cleaned = await self._cleanup_media_files(db)
                
                # Clean orphaned files
                orphaned_cleaned = await self._cleanup_orphaned_files()
                
                cleanup_stats = {
                    'person_records': person_cleaned,
                    'embedding_records': embedding_cleaned,
                    'media_files': media_cleaned,
                    'orphaned_files': orphaned_cleaned,
                    'total_cleaned': person_cleaned + embedding_cleaned + media_cleaned + orphaned_cleaned
                }
                
                logger.info(f"Cleanup completed:")
                logger.info(f"  - Person records cleaned: {person_cleaned}")
                logger.info(f"  - Embedding records cleaned: {embedding_cleaned}")
                logger.info(f"  - Media files cleaned: {media_cleaned}")
                logger.info(f"  - Orphaned files cleaned: {orphaned_cleaned}")
                
                # Update API status
                try:
                    from src.api.cleanup import update_cleanup_status
                    update_cleanup_status(datetime.utcnow(), cleanup_stats)
                except Exception as e:
                    logger.warning(f"Failed to update cleanup status: {e}")
                
                break  # Exit the async generator
                
        except Exception as e:
            logger.error(f"Cleanup process failed: {e}")
    
    async def _cleanup_person_data(self, db: AsyncSession) -> int:
        """Clean up old person data."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.person_data_retention_days)
            
            # Count records to be deleted
            count_result = await db.execute(
                select(PersonAppearance).where(PersonAppearance.created_at < cutoff_date)
            )
            count = len(count_result.scalars().all())
            
            if count > 0:
                # Delete old person appearances
                await db.execute(
                    delete(PersonAppearance).where(PersonAppearance.created_at < cutoff_date)
                )
                
                # Delete old person matches
                await db.execute(
                    delete(PersonMatch).where(PersonMatch.created_at < cutoff_date)
                )
                
                await db.commit()
                logger.info(f"Cleaned {count} person appearance records older than {self.person_data_retention_days} days")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup person data: {e}")
            await db.rollback()
            return 0
    
    async def _cleanup_embedding_data(self, db: AsyncSession) -> int:
        """Clean up old embedding data."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.embedding_data_retention_days)
            
            # Count records to be deleted
            count_result = await db.execute(
                select(PersonEmbedding).where(PersonEmbedding.created_at < cutoff_date)
            )
            count = len(count_result.scalars().all())
            
            if count > 0:
                # Delete old embeddings
                await db.execute(
                    delete(PersonEmbedding).where(PersonEmbedding.created_at < cutoff_date)
                )
                
                await db.commit()
                logger.info(f"Cleaned {count} embedding records older than {self.embedding_data_retention_days} days")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup embedding data: {e}")
            await db.rollback()
            return 0
    
    async def _cleanup_media_files(self, db: AsyncSession) -> int:
        """Clean up old media files."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.media_retention_days)
            
            # Get old media files from database
            result = await db.execute(text("""
                SELECT file_path FROM person_appearances 
                WHERE created_at < :cutoff_date AND file_path IS NOT NULL
                UNION
                SELECT file_path FROM person_embeddings 
                WHERE created_at < :cutoff_date AND file_path IS NOT NULL
            """), {"cutoff_date": cutoff_date})
            
            file_paths = [row[0] for row in result.fetchall()]
            cleaned_count = 0
            
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned {cleaned_count} media files older than {self.media_retention_days} days")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup media files: {e}")
            return 0
    
    async def _cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files in storage directories."""
        try:
            storage_dirs = [
                "storage/person_images",
                "storage/embeddings",
                "storage/temp"
            ]
            
            cleaned_count = 0
            
            for storage_dir in storage_dirs:
                dir_path = Path(storage_dir)
                if not dir_path.exists():
                    continue
                
                # Find files older than retention period
                cutoff_time = time.time() - (self.media_retention_days * 24 * 3600)
                
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            if file_path.stat().st_mtime < cutoff_time:
                                file_path.unlink()
                                cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete orphaned file {file_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned {cleaned_count} orphaned files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned files: {e}")
            return 0
    
    async def manual_cleanup(self, days: Optional[int] = None) -> Dict[str, int]:
        """Run manual cleanup with custom retention period."""
        if days:
            original_retention = self.person_data_retention_days
            self.person_data_retention_days = days
            self.embedding_data_retention_days = days
            self.media_retention_days = days
        
        try:
            async for db in get_db():
                person_cleaned = await self._cleanup_person_data(db)
                embedding_cleaned = await self._cleanup_embedding_data(db)
                media_cleaned = await self._cleanup_media_files(db)
                orphaned_cleaned = await self._cleanup_orphaned_files()
                
                return {
                    'person_records': person_cleaned,
                    'embedding_records': embedding_cleaned,
                    'media_files': media_cleaned,
                    'orphaned_files': orphaned_cleaned,
                    'total_cleaned': person_cleaned + embedding_cleaned + media_cleaned + orphaned_cleaned
                }
        finally:
            if days:
                self.person_data_retention_days = original_retention


# Global cleanup service instance
_cleanup_service: Optional[PeriodicCleanupService] = None


def get_cleanup_service() -> PeriodicCleanupService:
    """Get global cleanup service instance."""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = PeriodicCleanupService()
    return _cleanup_service


async def start_cleanup_scheduler():
    """Start the cleanup scheduler."""
    service = get_cleanup_service()
    await service.start_cleanup_scheduler()


async def run_manual_cleanup(days: Optional[int] = None) -> Dict[str, int]:
    """Run manual cleanup."""
    service = get_cleanup_service()
    return await service.manual_cleanup(days)
