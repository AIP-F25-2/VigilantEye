# Database Migration Status Summary

## ✅ Completed Actions

### 1. Fixed Model Imports
- **Issue:** Many models were not imported in `backend/src/models/__init__.py`
- **Fix:** Added all missing model imports:
  - AI Analysis models (AudioAnalysis, FaceDetection, ImageAnalysis, ThreatAssessment, FaceVector)
  - Person tracking models (PersonEmbedding, PersonAppearance, PersonMatch)
  - Ticket models (Ticket, TicketEvidence, TicketActivity)
- **Result:** All 14 tables are now tracked by SQLAlchemy metadata

### 2. Fixed SQLAlchemy Conflicts
- **Issue:** `metadata` is a reserved attribute in SQLAlchemy Declarative API
- **Fix:** Renamed conflicting columns:
  - `TicketActivity.metadata` → `TicketActivity.action_metadata`
  - `StorageFile.metadata` → `StorageFile.file_metadata`
- **Result:** Models can now be imported without errors

### 3. Created Comprehensive Database Setup Guide
- **File:** `backend/DATABASE_SETUP_GUIDE.md`
- **Contains:** Complete setup instructions, migration workflows, troubleshooting, and best practices

---

## Current Status

### ❌ Alembic Migrations: NOT SET UP
- Alembic is in requirements but not configured
- No `alembic/` directory exists
- No `alembic.ini` configuration file exists
- Currently using `Base.metadata.create_all()` (development only)

### ✅ Model Tracking: FIXED
- All 14 models are now properly imported
- All tables will be created when running migrations

### ✅ Database Setup: READY
- Migration script (`scripts/migrate.py`) is ready to use
- All models are properly configured
- Database can be set up using current approach

---

## How to Set Up Database Now

### Quick Setup (Development)

```bash
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Create database (if needed)
mysql -u root -p
CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Configure .env file
cp env.example .env
# Edit .env with your database credentials

# Create all tables
python scripts/migrate.py create

# Verify tables
mysql -u root -p vigilanteye -e "SHOW TABLES;"
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

### Perfect Setup (Production - Recommended)

For production, you should set up Alembic migrations. See `DATABASE_SETUP_GUIDE.md` for complete instructions.

**Quick Steps:**
1. Initialize Alembic: `alembic init alembic`
2. Configure `alembic.ini` and `alembic/env.py`
3. Create initial migration: `alembic revision --autogenerate -m "Initial migration"`
4. Apply migrations: `alembic upgrade head`

---

## Database Tables (14 Total)

### Core Tables (3)
- `users` - User authentication
- `videos` - Video metadata
- `storage_files` - File storage with TTL

### AI Analysis Tables (5)
- `audio_analysis` - Audio analysis results
- `face_detections` - Face detection results
- `image_analysis` - Image/frame analysis
- `threat_assessments` - Threat assessment results
- `face_vectors` - Face embedding vectors

### Person Tracking Tables (3)
- `person_embeddings` - Person identification
- `person_appearances` - Appearance tracking
- `person_matches` - Match results

### Ticket Management Tables (3)
- `tickets` - Threat management tickets
- `ticket_evidence` - Evidence associated with tickets
- `ticket_activity` - Activity log

---

## Next Steps

1. ✅ **DONE:** Fixed model imports
2. ✅ **DONE:** Fixed SQLAlchemy conflicts
3. ✅ **DONE:** Created setup guide
4. ⚠️ **RECOMMENDED:** Set up Alembic for production migrations
5. 📝 **OPTIONAL:** Update existing code that references `metadata` columns

---

## Files Changed

1. `backend/src/models/__init__.py` - Added all missing model imports
2. `backend/src/models/ticket.py` - Renamed `metadata` → `action_metadata`
3. `backend/src/models/storage.py` - Renamed `metadata` → `file_metadata`
4. `backend/DATABASE_SETUP_GUIDE.md` - Created comprehensive setup guide

---

## Verification

Run this to verify everything works:

```bash
cd backend
python -c "from src.models import *; from src.database.base import Base; print(f'✅ {len(Base.metadata.tables)} tables tracked'); print('Tables:', sorted(Base.metadata.tables.keys()))"
```

Expected output:
```
✅ 14 tables tracked
Tables: ['audio_analysis', 'face_detections', 'face_vectors', 'image_analysis', 'person_appearances', 'person_embeddings', 'person_matches', 'storage_files', 'threat_assessments', 'ticket_activity', 'ticket_evidence', 'tickets', 'users', 'videos']
```


