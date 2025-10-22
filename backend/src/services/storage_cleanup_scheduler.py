"""Background scheduler for automatic storage cleanup."""

import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.session import DatabaseSession
from src.services.storage_manager import StorageManager
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageCleanupScheduler:
    """Scheduler for automatic storage cleanup."""

    def __init__(self):
        """Initialize cleanup scheduler."""
        self.is_running = False
        self.cleanup_task = None
        self.interval_minutes = settings.cleanup_interval_minutes

    async def cleanup_cycle(self):
        """Perform one cleanup cycle."""
        logger.info("Starting storage cleanup cycle")
        
        # Create database session
        db = DatabaseSession()
        async with db.get_session() as session:
            storage_manager = StorageManager(session)
            
            try:
                # Clean up expired files
                result = await storage_manager.cleanup_expired_files(limit=1000)
                
                logger.info(
                    f"Cleanup cycle completed: "
                    f"{result['deleted']} files deleted, "
                    f"{result['space_freed_mb']}MB freed"
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Cleanup cycle failed: {e}", exc_info=True)
                return None

    async def run(self):
        """Run cleanup scheduler continuously."""
        self.is_running = True
        logger.info(
            f"Storage cleanup scheduler started "
            f"(interval: {self.interval_minutes} minutes)"
        )
        
        while self.is_running:
            try:
                # Run cleanup
                await self.cleanup_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Cleanup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in cleanup scheduler: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(60)

    def start(self):
        """Start the cleanup scheduler."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self.run())
            logger.info("Cleanup scheduler task created")

    async def stop(self):
        """Stop the cleanup scheduler."""
        self.is_running = False
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup scheduler stopped")


# Global scheduler instance
_scheduler = None


def get_cleanup_scheduler() -> StorageCleanupScheduler:
    """Get global cleanup scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = StorageCleanupScheduler()
    return _scheduler


async def start_cleanup_scheduler():
    """Start the global cleanup scheduler."""
    scheduler = get_cleanup_scheduler()
    scheduler.start()
    logger.info("Storage cleanup scheduler started")


async def stop_cleanup_scheduler():
    """Stop the global cleanup scheduler."""
    scheduler = get_cleanup_scheduler()
    await scheduler.stop()
    logger.info("Storage cleanup scheduler stopped")
