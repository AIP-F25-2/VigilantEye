"""Database initialization and setup script."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.database.base import Base
from src.models.user import User, UserRole
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def create_database():
    """Create database if it doesn't exist."""
    try:
        # Connect to postgres database to create our database
        postgres_url = settings.database_url.replace('/vigilanteye', '/postgres')
        engine = create_async_engine(postgres_url)
        
        async with engine.begin() as conn:
            # Check if database exists
            result = await conn.execute(text("""
                SELECT 1 FROM pg_database WHERE datname = 'vigilanteye'
            """))
            
            if not result.fetchone():
                # Create database
                await conn.execute(text("CREATE DATABASE vigilanteye"))
                logger.info("Database 'vigilanteye' created successfully")
            else:
                logger.info("Database 'vigilanteye' already exists")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise


async def create_tables():
    """Create all database tables."""
    try:
        engine = create_async_engine(settings.database_url)
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All database tables created successfully")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


async def create_default_admin():
    """Create default admin user if it doesn't exist."""
    try:
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Check if admin user exists
            result = await session.execute(text("""
                SELECT id FROM users WHERE username = 'admin'
            """))
            
            if not result.fetchone():
                # Create default admin user
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                
                admin_user = User(
                    email="admin@vigilanteye.com",
                    username="admin",
                    full_name="System Administrator",
                    hashed_password=pwd_context.hash("admin123"),
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_verified=True
                )
                
                session.add(admin_user)
                await session.commit()
                logger.info("Default admin user created successfully")
                logger.info("Username: admin")
                logger.info("Password: admin123")
            else:
                logger.info("Admin user already exists")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        raise


async def setup_database():
    """Complete database setup."""
    logger.info("Starting database setup...")
    
    try:
        # Step 1: Create database
        await create_database()
        
        # Step 2: Create tables
        await create_tables()
        
        # Step 3: Create default admin
        await create_default_admin()
        
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


def main():
    """Main function."""
    asyncio.run(setup_database())


if __name__ == "__main__":
    main()
