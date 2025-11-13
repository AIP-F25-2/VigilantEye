# 🗄️ Database Setup Guide

## Current Issue
MySQL server is not running, causing connection errors when trying to login or use database features.

## Solutions

### Option 1: Start MySQL with Docker Compose (Recommended)

If you have Docker installed:

```bash
# Start MySQL and phpMyAdmin
docker-compose up -d db phpmyadmin

# Wait a few seconds for MySQL to start, then check
docker-compose ps
```

**Access phpMyAdmin**: http://localhost:8080
- Server: `db`
- Username: `root`
- Password: `rootpass`

### Option 2: Install and Start MySQL Locally

#### Windows (Using MySQL Installer)
1. Download MySQL Installer from: https://dev.mysql.com/downloads/installer/
2. Install MySQL Server
3. Start MySQL service:
   ```powershell
   # Check if MySQL service exists
   Get-Service -Name "*mysql*"
   
   # Start MySQL service
   Start-Service MySQL80
   # or
   net start MySQL80
   ```

#### Create Database and User
```sql
CREATE DATABASE flaskapi;
CREATE USER 'flaskuser'@'localhost' IDENTIFIED BY 'flaskpass';
GRANT ALL PRIVILEGES ON flaskapi.* TO 'flaskuser'@'localhost';
FLUSH PRIVILEGES;
```

### Option 3: Use SQLite (Quick Testing)

For quick testing without MySQL, you can temporarily use SQLite:

1. **Modify `config.py`** or set environment variable:
   ```python
   DATABASE_URL = 'sqlite:///vigilanteye.db'
   ```

2. **Or set environment variable**:
   ```powershell
   $env:DATABASE_URL = "sqlite:///vigilanteye.db"
   python run.py
   ```

### Option 4: Use XAMPP/WAMP (Windows)

1. Install XAMPP from: https://www.apachefriends.org/
2. Start MySQL from XAMPP Control Panel
3. Create database and user via phpMyAdmin (http://localhost/phpmyadmin)

## Current Configuration

The application expects:
- **Host**: localhost
- **Port**: 3306
- **Database**: flaskapi
- **Username**: flaskuser
- **Password**: flaskpass

## Verify Connection

After starting MySQL, test the connection:

```python
import pymysql
try:
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='flaskuser',
        password='flaskpass',
        database='flaskapi'
    )
    print("✅ MySQL connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## Run Migrations

Once MySQL is running:

```bash
flask db upgrade
```

This will create all necessary database tables.

---

**Quick Fix**: If you just want to test the application quickly, use SQLite (Option 3).

