# 🚀 Quick Fix: Use SQLite Instead of MySQL

## Problem
MySQL server is not running, causing login and database errors.

## Quick Solution: Use SQLite

SQLite is a file-based database that doesn't require a server. Perfect for development and testing!

### Step 1: Set Environment Variable

**PowerShell:**
```powershell
$env:DATABASE_URL = "sqlite:///vigilanteye.db"
```

**Command Prompt:**
```cmd
set DATABASE_URL=sqlite:///vigilanteye.db
```

### Step 2: Restart Your Server

Stop the current server (Ctrl+C) and restart:
```powershell
python run.py
```

### Step 3: Run Database Migrations

In a new terminal:
```powershell
$env:DATABASE_URL = "sqlite:///vigilanteye.db"
flask db upgrade
```

## What Happens

- A file called `vigilanteye.db` will be created in your project root
- All database tables will be created automatically
- You can now login and use the application!

## Permanent Fix (Optional)

To always use SQLite, you can modify `app/__init__.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///vigilanteye.db'  # Changed from MySQL to SQLite
)
```

## Switch Back to MySQL Later

When you're ready to use MySQL:
1. Start MySQL server
2. Set: `$env:DATABASE_URL = "mysql+pymysql://flaskuser:flaskpass@localhost:3306/flaskapi"`
3. Restart the server

---

**Note**: SQLite is perfect for development. For production, use MySQL or PostgreSQL.

