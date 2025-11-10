# VigilantEye Backend

Flask-based backend API with AI-powered video analysis.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Runtime dependencies (aggregated)
pip install -r requirements.txt

# Development tooling (runtime + dev extras)
pip install -r requirements.dev.txt

# Alternatively install the segmented files
pip install -r requirements/base.txt
pip install -r requirements/ai_services.txt
pip install -r requirements/development.txt
```

Use the aggregated `requirements.txt` when you need the complete runtime stack (API, Celery workers, and AI services). Use `requirements.dev.txt` when you want the runtime stack plus linting, testing, and developer tooling in one step. Install from the segmented files if you only require core services, want to speed up CI runs, or need to avoid the larger AI-related dependencies during development.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start Services (Docker Compose)

```bash
# From project root
docker-compose up -d mysql redis chromadb
```

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start Application

```bash
# Flask API
flask --app src.app:create_app run --host=0.0.0.0 --port=5000
# or
python -m flask --app src.app:create_app run --host=0.0.0.0 --port=5000

# Celery Worker (separate terminal)
celery -A src.celery_app:create_celery_app worker --loglevel=info

# Celery Beat (enable ENABLE_BEAT=true only after required tasks exist)
# celery -A src.celery_app:create_celery_app beat --loglevel=info
```

> **MySQL credentials:** The default docker-compose configuration uses `MYSQL_USER=vigilanteye_user` and `MYSQL_PASSWORD=vigilanteye_pass`. Update these values in `.env` and `docker-compose.yml` for production deployments.

## Database Setup

### 1. Start Database Services

```bash
# From project root
docker-compose up -d mysql redis chromadb

# Verify services are running
docker-compose ps
```

### 2. Initialize Database

```bash
cd backend

# Option A: Using initialization script (development)
python scripts/init_db.py

# Option B: Using Alembic migrations
alembic upgrade head
```

### 3. Create Initial Migration (if needed)

```bash
# Generate migration from models
alembic revision --autogenerate -m "Initial schema"

# Review the generated migration in migrations/versions/
# Apply the migration
alembic upgrade head
```

### 4. Verify Database

```bash
# Connect to MySQL
mysql -h localhost -u root -proot vigilanteye

# List tables
SHOW TABLES;

# Check a table structure
DESCRIBE users;
```

## Authentication & Authorization

### Overview

VigilentEye uses JWT-based authentication with access and refresh tokens. Tokens are stored in both Redis (fast validation) and MySQL (audit trail).

### User Roles

- **Staff**: Default role, can view and analyze videos, manage tickets
- **Admin**: Full access, can promote/demote users, delete videos

### API Endpoints

All auth endpoints are available at `/api/auth/*`.

#### Public Endpoints (No Authentication)

**POST /api/auth/signup**
- Create a new user account
- Request: `{"username": "string", "email": "string", "password": "string"}`
- Response: `{"message": "User created successfully", "user": {...}}`
- Default role: `staff`

**POST /api/auth/login**
- Authenticate and receive tokens
- Request: `{"username": "string", "password": "string"}`
- Response: `{"access_token": "string", "refresh_token": "string", "user": {...}, "expires_in": 3600}`
- Rate limited: 5 attempts per 15 minutes

**POST /api/auth/refresh**
- Refresh access token using refresh token
- Request: `{"refresh_token": "string"}`
- Response: `{"access_token": "string", "refresh_token": "string", "expires_in": 3600}`
- Old tokens are revoked (token rotation)

#### Protected Endpoints (Authentication Required)

**POST /api/auth/logout**
- Revoke current session
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"message": "Logged out successfully"}`

**GET /api/auth/me**
- Get current user information
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"user": {"id": "uuid", "username": "string", "email": "string", "role": "staff|admin", ...}}`

#### Admin-Only Endpoints

**POST /api/auth/promote-user**
- Promote user to admin role
- Headers: `Authorization: Bearer <admin_access_token>`
- Request: `{"user_id": "uuid"}`
- Response: `{"message": "User promoted to admin", "user": {...}}`

**POST /api/auth/demote-user**
- Demote admin to staff role
- Headers: `Authorization: Bearer <admin_access_token>`
- Request: `{"user_id": "uuid"}`
- Response: `{"message": "User demoted to staff", "user": {...}}`

### Token Management

- **Access Token**: Expires in 1 hour (`JWT_ACCESS_TOKEN_EXPIRES`); used for API authentication; cached in Redis with TTL.
- **Refresh Token**: Expires in 30 days (`JWT_REFRESH_TOKEN_EXPIRES`); rotated on each refresh; stored in Redis and MySQL.
- **Token Storage**: Redis for fast revocation checks; MySQL for historical sessions and audit trail.

### Using Authentication in Code

**Protect an endpoint:**

```python
from src.utils import require_auth, admin_only, get_current_user

@app.route("/api/videos")
@require_auth
def list_videos():
    user = get_current_user()
    return jsonify(videos)

@app.route("/api/admin/settings")
@admin_only
def admin_settings():
    return jsonify(settings)
```

**Role-based access:**

```python
from src.utils import require_role

@app.route("/api/tickets")
@require_role("admin", "staff")
def list_tickets():
    return jsonify(tickets)
```

### Security Features

- bcrypt password hashing with 12 rounds (`BCRYPT_LOG_ROUNDS`)
- JWT tokens with access and refresh rotation
- Login rate limiting (5 attempts per 15 minutes)
- Comprehensive audit logging for all auth events
- Redis token storage for rapid revocation checks
- CORS configured for frontend origins

### Default Admin User

A default admin user is created on first run:
- Username: `admin`
- Password: `admin123`
- Change this password immediately in production.

### Testing Authentication

**Using curl:**

```bash
# Signup
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"Password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Password123"}'

# Use token
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Using Python requests:**

```python
import requests

response = requests.post(
    "http://localhost:5000/api/auth/login",
    json={"username": "testuser", "password": "Password123"},
)
tokens = response.json()
access_token = tokens["access_token"]

response = requests.get(
    "http://localhost:5000/api/auth/me",
    headers={"Authorization": f"Bearer {access_token}"},
)
user = response.json()
```

### Troubleshooting

- **401 Unauthorized**: Verify bearer token is present and unexpired.
- **403 Forbidden**: Ensure the user has the required role and is active.
- **429 Too Many Requests**: Login rate limit exceeded; wait 15 minutes.
- **Token expired**: Use refresh token at `/api/auth/refresh` to obtain new tokens.

## Storage Management

### Overview

VigilentEye uses a hierarchical file storage system with automatic TTL-based cleanup. Files are organized by type and date for efficient management.

### Storage Structure

```
storage/
├── videos/YYYY/MM/DD/     # Videos with 2-hour TTL (date-partitioned)
├── frames/{video_id}/     # Transient frame extraction workspace (cleanup task purges)
├── audio/{video_id}/      # Transient audio extraction workspace (cleanup task purges)
├── evidence/{ticket_id}/  # Permanent evidence storage for frames/audio linked to tickets
└── reports/{ticket_id}/   # Generated reports
```

### File Operations

**StorageService** provides core file management:

```python
from src.services import StorageService

storage_service = StorageService()

# Save video
video, error = storage_service.save_video(
    file_obj=uploaded_file,
    user_id=current_user.id,
    camera_id=camera.id,
    upload_type="upload",
)

# Save frame (evidence)
evidence, error = storage_service.save_frame(
    frame_data=frame_bytes,
    ticket_id=ticket.id,
    video_id=video.id,
    timestamp=datetime.utcnow(),
    frame_number=42,
)

# Delete file (admin only)
success, error = storage_service.delete_file(
    file_id=video.id,
    file_type="video",
    user_id=admin.id,
    reason="Duplicate upload",
)

# Get file path for serving
filepath, error = storage_service.get_file_path(
    file_id=video.id,
    file_type="video",
)
```

### API Endpoints

All storage endpoints are available at `/api/storage/*`:

#### Admin-Only Endpoints

**DELETE /api/storage/videos/{video_id}**
- Delete video file and database record
- Headers: `Authorization: Bearer <admin_token>`
- Request: `{"reason": "Optional deletion reason"}`
- Response: `{"message": "Video deleted successfully"}`
- Returns 409 if video linked to open tickets

**DELETE /api/storage/evidence/{evidence_id}**
- Delete evidence file (permanent deletion, use with caution)
- Headers: `Authorization: Bearer <admin_token>`
- Request: `{"reason": "Legal requirement"}`
- Response: `{"message": "Evidence deleted successfully"}`
- Returns 409 if the linked ticket is still open

**GET /api/storage/quota/system**
- Get system-wide storage usage
- Headers: `Authorization: Bearer <admin_token>`
- Response: `{"used_bytes": 50000000000, "total_bytes": 500000000000, "free_bytes": 450000000000, "percentage": 10.0, "used_human": "50 GB", "total_human": "500 GB"}`

**POST /api/storage/cleanup/trigger**
- Manually trigger cleanup task (for testing or emergency)
- Headers: `Authorization: Bearer <admin_token>`
- Response: `{"message": "Cleanup task triggered", "task_id": "task-uuid"}`

#### User Endpoints

**GET /api/storage/quota/user/{user_id}**
- Get user's storage quota (users can only view their own, admins can view any)
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"user_id": "uuid", "used_bytes": 1500000000, "max_bytes": 10000000000, "percentage": 15.0, "used_human": "1.5 GB", "max_human": "10 GB"}`

**GET /api/storage/videos/{video_id}/download**
- Download video file (users can only download their own, admins can download any)
- Headers: `Authorization: Bearer <access_token>`
- Response: File download with appropriate Content-Type and Content-Disposition headers

**GET /api/storage/evidence/{evidence_id}/download**
- Download evidence file (users must be assigned to ticket, admins can download any)
- Headers: `Authorization: Bearer <access_token>`
- Response: File download

### TTL-Based Cleanup

**Automatic Cleanup:**
- Runs every 15 minutes via Celery Beat
- Deletes expired videos (2 hours after upload)
- Deletes expired person records and embeddings (2 hours after detection)
- Auto-closes tickets (2 hours after creation)
- Processes in batches of 1000 records to avoid long transactions

**Cleanup Task:**
```python
from src.tasks import cleanup_expired_files

# Manually trigger cleanup (admin only via API)
result = cleanup_expired_files.delay()

# Result includes metrics
# {"deleted_videos": 42, "deleted_persons": 15, "freed_bytes": 5000000000, "errors": []}
```

**What Gets Deleted:**
- Videos older than 2 hours (configurable via `VIDEO_TTL_HOURS`)
- Person records older than 2 hours (configurable via `PERSON_VECTOR_TTL_HOURS`)
- Person embeddings in ChromaDB (same TTL as person records)
- Frames/audio NOT linked to tickets (temporary processing files)

**What Stays Permanent:**
- Evidence files (frames/audio linked to tickets)
- Reports
- Audit logs
- Tickets (auto-closed but not deleted)

### Storage Quota

**Per-User Quota:**
- Default: 10 GB per user (configurable via `USER_QUOTA_MAX_GB`)
- Tracked in Redis for fast access
- Synced to database periodically
- Enforced on video upload

**System Quota:**
- Monitors total disk usage
- Warns when exceeds 80% (configurable via `SYSTEM_QUOTA_WARNING_PERCENTAGE`)
- Admins can view via `/api/storage/quota/system`

### File Integrity

**Checksum Verification:**
- SHA256 checksum calculated on upload
- Stored in database (`Video.checksum`, `Evidence.checksum`)
- Can be verified on download (optional)
- Detects file corruption or tampering

```python
import hashlib

# Verify file integrity
with open(filepath, "rb") as f:
    calculated_checksum = hashlib.sha256(f.read()).hexdigest()

if calculated_checksum != video.checksum:
    logger.error("File integrity check failed!")
```

### Configuration

**Environment Variables:**

```env
STORAGE_BASE_PATH=./storage
VIDEO_TTL_HOURS=2
PERSON_VECTOR_TTL_HOURS=2
TICKET_AUTO_CLOSE_HOURS=2
MAX_VIDEO_SIZE_MB=500
SUPPORTED_VIDEO_FORMATS=mp4,avi,mov,mkv
USER_QUOTA_MAX_GB=10
SYSTEM_QUOTA_WARNING_PERCENTAGE=80
CLEANUP_BATCH_SIZE=1000
CLEANUP_ENABLED=true
```

### Monitoring

**Metrics to Track:**
- Storage usage per user
- System-wide storage usage
- Cleanup task execution time
- Number of files deleted per cleanup run
- Disk space freed per cleanup run
- Failed file deletions (errors)

**Logs:**
- All file operations logged to AuditLog table
- Cleanup task logs include detailed metrics
- File access logged for security auditing

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "message": "Cleanup completed",
  "context": {
    "deleted_videos": 42,
    "deleted_persons": 15,
    "freed_bytes": 5000000000,
    "duration_ms": 1234
  }
}
```

### Troubleshooting

- **File not found on disk:** Check if file was manually deleted, verify storage path configuration, and review cleanup logs.
- **Quota exceeded:** Check user usage via `/api/storage/quota/user/{user_id}`, delete old videos, increase quota, or trigger cleanup.
- **Cleanup not running:** Ensure Celery Beat and workers are running, verify `CLEANUP_ENABLED=true`, and inspect Celery logs.
- **Cannot delete video:** Ensure associated tickets are closed or wait for auto-close window.

## Database Models

The application uses 8 core models:

- **User** - Authentication and access control (staff/admin roles)
- **Camera** - Camera sources (uploaded videos or live streams)
- **Video** - Video files with 2-hour TTL
- **Person** - Detected persons with ReID tracking (2-hour TTL)
- **Evidence** - Permanent storage of suspicious frames/audio
- **Ticket** - Incident management with auto-escalation
- **Session** - JWT token management
- **AuditLog** - Security audit trail

### TTL (Time-To-Live) Logic

- **Videos**: Automatically deleted after 2 hours (configurable via `VIDEO_TTL_HOURS`)
- **Person Records**: Automatically deleted after 2 hours (configurable via `PERSON_VECTOR_TTL_HOURS`)
- **Evidence**: Permanent storage (no TTL)
- **Tickets**: Auto-closed after 2 hours (configurable via `TICKET_AUTO_CLOSE_HOURS`)

Celery Beat tasks run cleanup jobs every 15 minutes.

## Database Migrations

### Create a New Migration

```bash
# Using helper script
./scripts/generate_migration.sh "Add new column to users"

# Or directly with Alembic
alembic revision --autogenerate -m "Add new column to users"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Migration Best Practices

1. Always review autogenerated migrations. Alembic may miss some changes.
2. Test migrations on a copy of production data before applying to production.
3. Add indexes manually for performance-critical columns.
4. Use batch operations for large table modifications.
5. Keep migrations small and focused. One logical change per migration.

## Database Utilities

The `src/utils/db_utils.py` module provides:

- `check_db_connection()` - Health check
- `retry_on_db_error()` - Retry decorator for transient errors
- `get_db_session()` - Context manager for sessions
- `batch_delete()` - Efficient batch deletion for TTL cleanup
- `get_pool_stats()` - Connection pool monitoring

Example usage:

```python
from src.utils.db_utils import retry_on_db_error, get_db_session

@retry_on_db_error(max_attempts=3)
def create_user(username, email):
    with get_db_session() as session:
        user = User(username=username, email=email)
        session.add(user)
        session.commit()
        return user
```

## Upload Guidelines

- Frontend upload validation checks MIME types listed in `frontend/src/utils/constants.ts` under `SUPPORTED_VIDEO_MIME_TYPES`.
- Backend services expect file extensions listed in `backend/src/config/constants.py` under `SUPPORTED_VIDEO_FORMATS`.
- When adding support for new formats, update both lists so MIME types and extensions stay aligned (for example, `video/mp4` ↔ `mp4`).

## Project Structure

```
backend/
├── src/
│   ├── api/          # REST API endpoints
│   ├── services/     # Business logic
│   ├── ai_modules/   # AI processing
│   ├── models/       # Database models
│   ├── utils/        # Utilities
│   ├── config/       # Configuration
│   └── tasks/        # Celery tasks
├── storage/          # Local file storage
├── models_cache/     # Downloaded AI models
├── tests/            # Test suite
└── requirements/     # Dependencies
```

## API Documentation

API will be available at `http://localhost:5000/api`

Health check: `http://localhost:5000/health`

## Testing

```bash
pytest tests/ --cov=src --cov-report=html
```

## Code Quality

```bash
black src/
flake8 src/
isort src/
mypy src/
```

