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
        # Connect to MySQL server without specifying database
        # Extract connection details from database URL
        db_url = settings.database_url
        
        # Parse MySQL URL: mysql+pymysql://user:pass@host:port/dbname
        # Remove database name to connect to MySQL server
        # For async URL, replace mysql+aiomysql with mysql+pymysql for sync operations
        if 'mysql+aiomysql' in db_url:
            sync_url = db_url.replace('mysql+aiomysql', 'mysql+pymysql')
        else:
            sync_url = db_url
        
        # Remove database name from URL
        if '/vigilanteye' in sync_url:
            mysql_url = sync_url.replace('/vigilanteye', '')
        elif '/vigilent_eye' in sync_url:
            mysql_url = sync_url.replace('/vigilent_eye', '')
        else:
            # Extract database name from URL
            db_name = settings.db_name
            mysql_url = sync_url.replace(f'/{db_name}', '')
        
        # Use sync engine for database creation
        from sqlalchemy import create_engine
        engine = create_engine(mysql_url)
        
        with engine.begin() as conn:
            # Check if database exists
            result = conn.execute(text(f"""
                SELECT SCHEMA_NAME 
                FROM INFORMATION_SCHEMA.SCHEMATA 
                WHERE SCHEMA_NAME = '{settings.db_name}'
            """))
            
            if not result.fetchone():
                # Create database with UTF8MB4 charset
                conn.execute(text(f"""
                    CREATE DATABASE `{settings.db_name}` 
                    CHARACTER SET utf8mb4 
                    COLLATE utf8mb4_unicode_ci
                """))
                logger.info(f"Database '{settings.db_name}' created successfully")
            else:
                logger.info(f"Database '{settings.db_name}' already exists")
        
        engine.dispose()
        
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
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
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
