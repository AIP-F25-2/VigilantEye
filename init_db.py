#!/usr/bin/env python3
"""
Database initialization script
Creates all tables defined in models.py
"""
from database import engine
from models import Base
from config import settings

def init_db():
    """Initialize the database by creating all tables"""
    print(f"Initializing database: {settings.DB_NAME}")
    print(f"Host: {settings.DB_HOST}:{settings.DB_PORT}")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        print("Tables created:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        print("\nMake sure:")
        print("1. MySQL server is running")
        print("2. Database exists")
        print("3. User has proper permissions")
        print("4. Environment variables are set correctly")

if __name__ == "__main__":
    init_db()
