#!/usr/bin/env python3
"""
Test script to verify MySQL connection and database setup
"""

try:
    import mysql.connector
    print("✓ mysql.connector imported successfully")
except ImportError as e:
    print(f"✗ Error importing mysql.connector: {e}")
    print("Please install: pip install mysql-connector-python")
    exit(1)

try:
    from config import Config
    print("✓ Config imported successfully")
    print(f"  MySQL Host: {Config.MYSQL_HOST}")
    print(f"  MySQL User: {Config.MYSQL_USER}")
    print(f"  MySQL Database: {Config.MYSQL_DATABASE}")
except ImportError as e:
    print(f"✗ Error importing config: {e}")
    exit(1)

try:
    from database import create_database, init_database
    print("✓ Database functions imported successfully")
    
    print("\n🔧 Testing database setup...")
    if create_database():
        print("✓ Database creation successful")
    else:
        print("✗ Database creation failed")
        
    if init_database():
        print("✓ Database initialization successful")
    else:
        print("✗ Database initialization failed")
        
except Exception as e:
    print(f"✗ Error testing database: {e}")
    print("\n💡 Make sure MySQL is running and credentials are correct in config.py")

print("\n✅ MySQL setup test completed!")
