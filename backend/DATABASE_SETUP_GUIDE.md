# Database Setup Guide

## Current Status

### ❌ **SQL Migrations Status: NOT PRESENT**

**Findings:**
- Alembic is listed in `requirements/base.txt` but **not configured**
- No `alembic/` directory exists
- No `alembic.ini` configuration file exists
- Currently using SQLAlchemy's `Base.metadata.create_all()` approach (not production-ready)

### ✅ **FIXED: Model Import Issue**

**Previous Issue:** Many models were NOT imported in `backend/src/models/__init__.py`, which prevented tables from being created.

**Status:** ✅ **FIXED** - All models are now properly imported:
- ✅ `User`, `UserRole` (from `user.py`)
- ✅ `Video`, `VideoStatus` (from `video.py`)
- ✅ `StorageFile`, `FileType`, `StorageStatus` (from `storage.py`)
- ✅ `Ticket`, `TicketEvidence`, `TicketActivity` (from `ticket.py`)
- ✅ `PersonEmbedding`, `PersonAppearance`, `PersonMatch` (from `person_embeddings.py`)
- ✅ `AudioAnalysis`, `FaceDetection`, `ImageAnalysis`, `ThreatAssessment`, `FaceVector` (from `ai_analysis.py`)

**Verification:** All 14 tables are now tracked by SQLAlchemy metadata.

**Note:** Fixed column name conflicts (`metadata` → `action_metadata` and `file_metadata`) to avoid SQLAlchemy reserved attribute conflicts.

---

## Database Tables Overview

Your database should have the following tables:

1. **Core Tables:**
   - `users` - User authentication and authorization
   - `videos` - Video metadata and processing status
   - `storage_files` - File storage tracking with TTL

2. **AI Analysis Tables:**
   - `audio_analysis` - Audio analysis results
   - `face_detections` - Face detection results
   - `image_analysis` - Image/frame analysis results
   - `threat_assessments` - Threat assessment results
   - `face_vectors` - Face embedding vectors

3. **Person Tracking Tables:**
   - `person_embeddings` - Person identification embeddings
   - `person_appearances` - Person appearance tracking
   - `person_matches` - Person match results

4. **Ticket Management Tables:**
   - `tickets` - Threat management tickets
   - `ticket_evidence` - Evidence associated with tickets
   - `ticket_activity` - Ticket activity log

---

## Perfect Database Setup Guide

### Option 1: Quick Setup (Current Method - Development Only)

**⚠️ Warning:** This method uses `create_all()` which is **NOT recommended for production**. Use only for development.

```bash
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Ensure all models are imported (IMPORTANT!)
# The models/__init__.py must import all models

# 4. Create database (if using MySQL locally)
mysql -u root -p
CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# 5. Configure environment
cp env.example .env
# Edit .env with your database credentials

# 6. Run migrations to create tables
python scripts/migrate.py create

# 7. Verify tables were created
mysql -u root -p vigilanteye
SHOW TABLES;
```

**Expected Output:**
```
+----------------------------+
| Tables_in_vigilanteye      |
+----------------------------+
| users                      |
| videos                     |
| storage_files              |
| audio_analysis             |
| face_detections            |
| image_analysis             |
| threat_assessments         |
| face_vectors               |
| person_embeddings          |
| person_appearances         |
| person_matches             |
| tickets                    |
| ticket_evidence            |
| ticket_activity            |
+----------------------------+
```

### Option 2: Proper Alembic Setup (Recommended for Production)

#### Step 1: Initialize Alembic

```bash
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Initialize Alembic
alembic init alembic
```

#### Step 2: Configure Alembic

Edit `alembic.ini`:

```ini
# Change this line:
sqlalchemy.url = driver://user:pass@localhost/dbname

# To:
sqlalchemy.url = mysql+pymysql://root:password@localhost:3306/vigilanteye

# Or better, use environment variable (see env.py configuration below)
```

Edit `alembic/env.py`:

```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.database.base import Base
from src.models import *  # Import all models (IMPORTANT!)

# Use settings from your config
settings = get_settings()

# Get database URL from settings
config = context.config
config.set_main_option('sqlalchemy.url', settings.database_url)

# Set target metadata
target_metadata = Base.metadata
```

#### Step 3: Create Initial Migration

```bash
# Create initial migration (includes all current models)
alembic revision --autogenerate -m "Initial migration - all tables"

# Review the generated migration file in alembic/versions/
# Make sure it includes all tables
```

#### Step 4: Apply Migrations

```bash
# Apply migrations to create tables
alembic upgrade head

# Verify
alembic current
```

#### Step 5: Verify Database Setup

```bash
# Check migration status
alembic current
alembic history

# Verify tables in database
mysql -u root -p vigilanteye
SHOW TABLES;
```

### Option 3: Using Docker Compose (Easiest)

```bash
# From project root
docker-compose up -d mysql

# Wait for MySQL to be ready (30-60 seconds)
docker-compose ps

# Run migrations
cd backend
python scripts/migrate.py create

# Or if using Alembic:
alembic upgrade head
```

---

## Database Setup Scripts

### Current Scripts:

1. **`scripts/setup_database.py`** - Creates database and tables (MySQL-focused)
   - ✅ **Status:** Uses MySQL syntax and properly creates database
   - ✅ **Status:** Imports all models correctly

2. **`scripts/migrate.py`** - Creates/drops tables using SQLAlchemy
   - ⚠️ **Issue:** Relies on `from src.models import *` but not all models are exported
   - ✅ **Status:** Works but missing models won't be created

3. **`scripts/init_db.sql`** - MySQL initialization script
   - ✅ **Status:** Only creates database, not tables

### Recommended Setup Process:

```bash
# 1. Ensure all models are imported in models/__init__.py
# (This has been fixed)

# 2. Create database manually or use init_db.sql
mysql -u root -p < scripts/init_db.sql

# 3. Run migration script
python scripts/migrate.py create

# 4. Verify all tables exist
python -c "
from src.database.base import Base
from src.models import *
print('Tables:', list(Base.metadata.tables.keys()))
"
```

---

## Verification Checklist

After setup, verify:

- [ ] Database `vigilanteye` exists
- [ ] All 14 tables exist (see list above)
- [ ] Default admin user exists (if using setup_database.py)
- [ ] Foreign key constraints are properly set up
- [ ] Indexes are created
- [ ] Can connect from application

### Verification Commands:

```bash
# Check database connection
python -c "
from src.config import get_settings
from src.database.session import DatabaseSession
import asyncio

async def test():
    db = DatabaseSession()
    db.initialize()
    print('✅ Database connection successful')
    await db.close()

asyncio.run(test())
"

# Check all tables exist
mysql -u root -p vigilanteye -e "SHOW TABLES;"

# Check table structure
mysql -u root -p vigilanteye -e "DESCRIBE users;"
mysql -u root -p vigilanteye -e "DESCRIBE videos;"
mysql -u root -p vigilanteye -e "DESCRIBE tickets;"
```

---

## Migration Workflow (If Using Alembic)

### Creating New Migrations:

```bash
# 1. Make changes to models in src/models/

# 2. Create migration
alembic revision --autogenerate -m "Description of changes"

# 3. Review generated migration file
# Edit alembic/versions/XXXX_description.py if needed

# 4. Apply migration
alembic upgrade head

# 5. Verify
alembic current
```

### Rolling Back Migrations:

```bash
# Show migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

---

## Troubleshooting

### Issue: Tables Not Created

**Symptom:** Running `migrate.py create` but tables don't exist

**Solution:**
1. Check if all models are imported in `src/models/__init__.py`
2. Verify models inherit from `Base`
3. Check database connection in `.env`
4. Review logs for errors

### Issue: Foreign Key Constraint Errors

**Symptom:** `Cannot add foreign key constraint`

**Solution:**
- Ensure parent tables are created first
- Check table creation order matches dependencies
- Verify foreign key column types match

### Issue: Model Import Errors

**Symptom:** `ImportError: cannot import name 'X'`

**Solution:**
- Ensure all models are in `models/__init__.py`
- Check for circular imports
- Verify all dependencies are installed

### Issue: Alembic Not Finding Models

**Symptom:** `alembic revision --autogenerate` creates empty migration

**Solution:**
- Ensure `alembic/env.py` imports all models: `from src.models import *`
- Verify `target_metadata = Base.metadata` is set
- Check that models inherit from `Base`

---

## Best Practices

1. **Always use migrations in production** - Never use `create_all()` in production
2. **Review auto-generated migrations** - Alembic can miss some changes
3. **Test migrations** - Test on development database first
4. **Backup before migrations** - Always backup production database
5. **Version control migrations** - Commit migration files to git
6. **Document schema changes** - Comment complex migrations
7. **Use migration dependencies** - Link related migrations when needed

---

## Next Steps

1. ✅ **IMMEDIATE:** Fix `models/__init__.py` to import all models
2. ⚠️ **RECOMMENDED:** Set up Alembic for proper migrations
3. ✅ **VERIFY:** Test database setup with all tables
4. 📝 **DOCUMENT:** Update setup scripts to use Alembic
5. 🔄 **MAINTAIN:** Create migration workflow documentation

---

## Quick Reference

```bash
# Current approach (development)
python scripts/migrate.py create    # Create tables
python scripts/migrate.py drop      # Drop tables
python scripts/migrate.py reset     # Drop and recreate

# Alembic approach (production)
alembic revision --autogenerate -m "message"  # Create migration
alembic upgrade head                         # Apply migrations
alembic downgrade -1                         # Rollback
alembic current                              # Check current version
alembic history                              # View history
```

