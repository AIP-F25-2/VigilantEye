import pymysql
from config import Config

def get_db_connection():
    """Create and return a MySQL database connection (PyMySQL)."""
    try:
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return connection
    except Exception as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def init_database():
    """Initialize the database and create tables if they don't exist"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Create users table
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_users_table)
        connection.commit()
        print("Database initialized successfully!")
        return True
        
    except Exception as err:
        print(f"Error initializing database: {err}")
        return False
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def create_database():
    """Create the database if it doesn't exist"""
    try:
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DATABASE}")
        connection.commit()
        print(f"Database '{Config.MYSQL_DATABASE}' created or already exists")
        return True
    except Exception as err:
        print(f"Error creating database: {err}")
        return False
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass
