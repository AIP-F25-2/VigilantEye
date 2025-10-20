"""Database migration script."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.database.base import Base
from src.database.session import DatabaseSession
from src.models import *  # Import all models
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


async def create_tables():
    """Create all database tables."""
    settings = get_settings()
    db = DatabaseSession()
    db.initialize()
    
    logger.info("Creating database tables...")
    
    async with db.engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    await db.close()


async def drop_tables():
    """Drop all database tables."""
    settings = get_settings()
    db = DatabaseSession()
    db.initialize()
    
    logger.warning("Dropping all database tables...")
    
    async with db.engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("Database tables dropped")
    await db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "command",
        choices=["create", "drop", "reset"],
        help="Migration command to execute",
    )
    
    args = parser.parse_args()
    
    if args.command == "create":
        asyncio.run(create_tables())
    elif args.command == "drop":
        asyncio.run(drop_tables())
    elif args.command == "reset":
        asyncio.run(drop_tables())
        asyncio.run(create_tables())
