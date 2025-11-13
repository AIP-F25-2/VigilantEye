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

## Video Processing

### Overview

VigilentEye processes uploaded videos and RTSP live streams using OpenCV for video operations and FFmpeg for audio extraction. The system supports concurrent stream management, motion detection, and automatic metadata extraction.

### Features

- **Video Upload**: Upload videos with automatic metadata extraction (duration, fps, resolution)
- **Thumbnail Generation**: Automatic thumbnail creation (320x240) from first frame
- **Frame Extraction**: Extract frames at configurable intervals (default 1 second)
- **Motion Detection**: Skip static frames using adaptive frame extraction
- **Audio Extraction**: Extract audio tracks using FFmpeg/pydub
- **RTSP Streaming**: Support for live camera streams with concurrent stream management
- **Frame Buffering**: Memory-safe frame buffering (max 100 frames per stream)
- **Video Validation**: Format, size, and resolution validation before processing

### VideoProcessorService

Core video processing operations:

```python
from src.services import VideoProcessorService

video_processor = VideoProcessorService()

# Extract metadata
metadata, error = video_processor.extract_metadata(video_path)
# Returns: {'duration': 120.5, 'fps': 30.0, 'resolution': '1920x1080', ...}

# Generate thumbnail
success, error = video_processor.generate_thumbnail(
    video_path=video_path,
    output_path=thumbnail_path,
    size=(320, 240)
)

# Extract frames with motion detection
frames, error = video_processor.extract_frames(
    video_path=video_path,
    output_dir=frames_dir,
    interval=1.0,  # seconds
    use_motion_detection=True
)

# Extract audio
success, error = video_processor.extract_audio(
    video_path=video_path,
    output_path=audio_path
)

# Process uploaded video (metadata + thumbnail)
video, error = video_processor.process_uploaded_video(video)
```

### API Endpoints

All video endpoints are available at `/api/videos/*`:

#### Upload Video

**POST /api/videos/upload**
- Upload video file with automatic processing
- Headers: `Authorization: Bearer <access_token>`
- Content-Type: `multipart/form-data`
- Form data: `video` (file), `camera_id` (optional)
- Response: `{"message": "Video uploaded successfully", "video": {...}}`
- Upload flow is two-step: `StorageService.save_video()` writes the file and creates the record, then `VideoProcessorService.process_uploaded_video()` populates metadata and thumbnails after validation.
- Automatically extracts metadata and generates thumbnail
- Enforces quota limits and file size limits

#### Start Live Stream

**POST /api/videos/start-stream**
- Start RTSP live stream capture
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"camera_id": "uuid", "stream_url": "rtsp://...", "name": "Camera 1"}`
- Response: `{"message": "Stream started successfully", "camera_id": "uuid", "video_id": "uuid"}`
- Maximum concurrent streams: 4 (configurable)
- Frames buffered in memory for real-time processing

#### Stop Live Stream

**POST /api/videos/stop-stream**
- Stop active RTSP stream
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"camera_id": "uuid"}`
- Response: `{"message": "Stream stopped successfully"}`

#### List Videos

**GET /api/videos**
- List user's videos with pagination and filtering
- Headers: `Authorization: Bearer <access_token>`
- Query params: `page`, `per_page`, `status`, `camera_id`, `upload_type`
- Response: `{"videos": [...], "pagination": {...}}`
- Users see only their videos; admins see all videos

#### Get Video Details

**GET /api/videos/{video_id}**
- Get detailed video information
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"video": {"id": "uuid", "filename": "...", "duration": 120.5, "fps": 30.0, "resolution": "1920x1080", ...}}`

#### Get Thumbnail

**GET /api/videos/{video_id}/thumbnail**
- Download video thumbnail image
- Headers: `Authorization: Bearer <access_token>`
- Response: JPEG image file
- Content-Type: `image/jpeg`

#### Get Active Streams

**GET /api/videos/streams/active**
- List currently active RTSP streams
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"active_streams": [...], "count": 2, "max_streams": 4}`

### Configuration

**Environment Variables:**

```env
# Video Processing
FRAME_EXTRACTION_INTERVAL=1.0          # Seconds between extracted frames
MAX_CONCURRENT_STREAMS=4               # Maximum simultaneous RTSP streams
MOTION_DETECTION_THRESHOLD=0.3         # Motion sensitivity (0.0-1.0)
THUMBNAIL_WIDTH=320                    # Thumbnail width in pixels
THUMBNAIL_HEIGHT=240                   # Thumbnail height in pixels
MAX_RESOLUTION_WIDTH=3840              # Maximum video width (4K)
MAX_RESOLUTION_HEIGHT=2160             # Maximum video height (4K)
FFMPEG_PATH=ffmpeg                     # Path to FFmpeg binary
FRAME_BUFFER_SIZE=100                  # Max frames buffered per stream
```

### Motion Detection

**How it works:**
- Compares consecutive frames using frame differencing
- Converts frames to grayscale and applies Gaussian blur
- Calculates absolute difference between frames
- Applies threshold to detect motion
- Skips frames with motion score below threshold
- Configurable sensitivity via `MOTION_DETECTION_THRESHOLD`

**Benefits:**
- Reduces storage requirements (skip static frames)
- Focuses on frames with activity
- Improves AI analysis efficiency

### Stream Management

**Concurrent Streams:**
- Maximum 4 concurrent streams (configurable)
- Each stream runs in separate thread
- Frame buffering prevents memory overflow
- Automatic reconnection on stream failure (3 retries)
- Graceful shutdown on stop request

**Frame Buffering:**
- Uses `collections.deque` with max size (default 100 frames)
- Oldest frames automatically dropped when buffer full
- Thread-safe access with locks
- Frames available for real-time processing

### Dependencies

**Required:**
- **OpenCV** (opencv-python==4.8.1.78) - Video processing
- **FFmpeg** - Audio extraction (must be installed on system)
- **pydub** (0.25.1) - FFmpeg wrapper for Python
- **Pillow** (10.1.0) - Image processing
- **NumPy** (1.26.2) - Array operations

**Installing FFmpeg:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Add to PATH
```

### Video Validation

**Checks performed:**
- File format (mp4, avi, mov, mkv)
- File size (max 500 MB, configurable)
- Video can be opened by OpenCV
- Resolution within limits (max 4K)
- First frame can be read

**Validation errors:**
- 400: Invalid format or corrupted video
- 413: File too large
- 409: Quota exceeded

### Troubleshooting

**FFmpeg not found:**
- Error: "FFmpeg not installed"
- Solution: Install FFmpeg and ensure it's in PATH
- Or set `FFMPEG_PATH` environment variable to full path

**Video cannot be opened:**
- Check video format is supported
- Verify file is not corrupted
- Try re-encoding with FFmpeg: `ffmpeg -i input.avi -c:v libx264 output.mp4`

**Stream connection fails:**
- Verify RTSP URL is correct
- Check network connectivity to camera
- Ensure camera supports RTSP protocol
- Check firewall settings

**Max concurrent streams reached:**
- Stop inactive streams: `POST /api/videos/stop-stream`
- Increase limit: set `MAX_CONCURRENT_STREAMS` environment variable
- Check active streams: `GET /api/videos/streams/active`

**Thumbnail not generated:**
- Check video has at least one frame
- Verify storage directory is writable
- Check logs for OpenCV errors

### Performance Considerations

**Video Upload:**
- Metadata extraction is fast (~1 second for typical video)
- Thumbnail generation is fast (~0.5 seconds)
- Processing happens synchronously during upload
- Heavy AI analysis deferred to separate pipeline

**Frame Extraction:**
- Motion detection adds ~10-20% overhead
- Adaptive extraction reduces storage by 50-80%
- Parallel processing possible for multiple videos

**Streaming:**
- Each stream consumes ~50-100 MB RAM (with buffering)
- CPU usage depends on frame rate and resolution
- Recommended: 2 CPU cores per 4 concurrent streams
- Network bandwidth: ~2-5 Mbps per HD stream

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

## AI Modules: Person Detection & Re-Identification

### Overview

VigilentEye uses state-of-the-art AI models for person detection, face recognition, and re-identification across video frames. The system tracks individuals, estimates demographics, and stores embeddings for similarity search.

### Features

- **Person Detection**: YOLOv8-nano for fast, accurate person detection
- **Face Detection**: MTCNN for robust face detection in various conditions
- **Face Recognition**: ArcFace embeddings for face similarity matching
- **Person Re-Identification**: OSNet for tracking persons across frames and cameras
- **Demographics**: MiVOLO for age, gender, and ethnicity estimation
- **Clothing Analysis**: Color and pattern detection for person description
- **Vector Storage**: ChromaDB for embedding storage with 2-hour TTL
- **Similarity Search**: Fast person matching using ChromaDB's HNSW index

### AI Models Used

**All models are open-source and run locally (no API costs):**

1. **YOLOv8-nano** (Ultralytics)
   - Purpose: Person detection in frames
   - Size: ~6 MB
   - Speed: ~100 FPS on GPU, ~20 FPS on CPU
   - License: AGPL-3.0

2. **MTCNN** (Multi-task Cascaded CNN)
   - Purpose: Face detection and alignment
   - Size: ~2 MB
   - Accuracy: High precision even with occlusions
   - License: MIT

3. **ArcFace** (InceptionResnetV1)
   - Purpose: Face embeddings for recognition
   - Embedding size: 512-D
   - Pretrained on: VGGFace2 dataset
   - License: MIT (via facenet-pytorch)

4. **OSNet** (Omni-Scale Network)
   - Purpose: Person re-identification across frames
   - Embedding size: 512-D
   - Variants: osnet_x1_0 (best accuracy), osnet_x0_5 (faster)
   - License: MIT (via torchreid)

5. **MiVOLO** (Multi-input Vision Transformer)
   - Purpose: Age, gender, and ethnicity estimation
   - Input: Face + body context
   - Accuracy: State-of-the-art on IMDB-WIKI dataset
   - License: MIT

### PersonDetectorService

**Core person detection and tracking:**

```python
from src.ai_modules import PersonDetectorService

person_detector = PersonDetectorService()

# Detect persons in a frame
persons, error = person_detector.detect_persons(
    frame=frame_array,  # numpy array (H, W, 3)
    video_id=video.id,
    timestamp=datetime.utcnow(),
    frame_number=42
)

# Returns list of detected persons:
# [
#   {
#     'person_id': 'uuid',
#     'person_tracking_id': 'person_abc123',
#     'bbox': [x1, y1, x2, y2],
#     'age': 30,
#     'gender': 'male',
#     'ethnicity': 'caucasian',
#     'confidence': 0.85,
#     'clothing_description': 'Dark jacket, blue jeans',
#     'body_features': {'height_ratio': 1.8, 'aspect_ratio': 0.45},
#     'embeddings': {'face': [...], 'body': [...]},
#     'first_seen': '2024-01-15T10:30:00Z',
#     'last_seen': '2024-01-15T10:30:00Z',
#     'total_appearances': 1
#   }
# ]

# Find similar persons (for reports)
similar, error = person_detector.find_similar_persons(
    person_id=person.id,
    time_window_hours=2,
    top_k=10
)
# Returns persons with similar face/body embeddings from same timeframe
```

### Person Re-Identification (ReID)

**How it works:**
1. Extract OSNet embedding (512-D) from person crop
2. Search ChromaDB for similar embeddings (cosine similarity)
3. If match found (similarity > 0.8), reuse existing person_tracking_id
4. If no match, generate new person_tracking_id
5. Update first_seen/last_seen timestamps
6. Track total_appearances across frames

**Benefits:**
- Track persons across multiple frames and cameras
- Identify when same person appears multiple times
- Build timeline of person's movements
- Link persons to multiple incidents

**Similarity Threshold:**
- Default: 0.8 (80% similar)
- Configurable via `REID_SIMILARITY_THRESHOLD`
- Higher = stricter matching (fewer false positives)
- Lower = looser matching (more false positives)

### Vector Database (ChromaDB)

**Collections:**
- `face_embeddings`: ArcFace 512-D vectors for face recognition
- `body_embeddings`: OSNet 512-D vectors for person ReID

**Metadata Stored:**
- `person_id`: UUID linking to Person table
- `video_id`: Source video
- `timestamp`: When detected (epoch seconds)
- `expires_at`: TTL expiration timestamp (epoch seconds)
- `confidence`: Detection confidence score

**TTL Management:**
- Embeddings expire after 2 hours (configurable via `PERSON_VECTOR_TTL_HOURS`)
- Cleanup task runs every 15 minutes via Celery Beat
- Expired embeddings deleted automatically
- Embeddings linked to tickets have TTL cleared (permanent storage)

**Similarity Search:**
- Uses ChromaDB's native HNSW index (fast approximate nearest neighbor)
- Distance metric: Cosine similarity
- Query time: ~10ms for 10k embeddings
- Returns top-k most similar persons with similarity scores

### Model Download & Caching

**First Run:**
- Models downloaded automatically from Hugging Face, PyTorch Hub, Ultralytics
- Total download size: ~200 MB (all models combined)
- Download time: ~2-5 minutes (depends on internet speed)
- Models saved to `models_cache/` directory

**Subsequent Runs:**
- Models loaded from local cache (instant)
- No network requests needed
- Startup time: ~5-10 seconds (model loading)

**Model Locations:**
```
models_cache/
├── yolov8/yolov8n.pt          (~6 MB)
├── mtcnn/                     (~2 MB, auto-cached by library)
├── arcface/                   (~100 MB, cached in ~/.cache/torch/)
├── osnet/osnet_x1_0.pth      (~3 MB, cached in ~/.cache/torch/)
└── mivolo/                    (~100 MB, Hugging Face cache)
```

### Configuration

**Environment Variables:**
```env
# Person Detection
PERSON_DETECTION_CONFIDENCE=0.5        # Min confidence for person detection
FACE_DETECTION_CONFIDENCE=0.9          # Min confidence for face detection
REID_SIMILARITY_THRESHOLD=0.8          # Similarity threshold for ReID matching
MAX_PERSONS_PER_FRAME=50               # Max persons to process per frame
PERSON_MIN_SIZE=50                     # Min bounding box size (pixels)
SAVE_PERSON_THUMBNAILS=true            # Save person thumbnails
USE_GPU_INFERENCE=true                 # Use GPU if available

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_COLLECTION_NAME=vigilanteye_vectors

# TTL
PERSON_VECTOR_TTL_HOURS=2              # Embedding expiration time
```

### Performance Considerations

**Inference Speed (per frame):**
- YOLOv8 person detection: ~50ms (GPU), ~200ms (CPU)
- MTCNN face detection: ~30ms per face (GPU), ~100ms (CPU)
- ArcFace embedding: ~10ms per face (GPU), ~50ms (CPU)
- OSNet embedding: ~20ms per person (GPU), ~80ms (CPU)
- MiVOLO demographics: ~30ms per face (GPU), ~100ms (CPU)
- **Total per person**: ~140ms (GPU), ~530ms (CPU)
- **For 5 persons**: ~700ms (GPU), ~2.6s (CPU)

**Memory Usage:**
- Models in memory: ~500 MB (all models loaded)
- ChromaDB: ~100 MB per 10k embeddings
- Per-frame processing: ~50 MB (temporary tensors)

**Optimization Tips:**
- Use GPU for 4-5x speedup
- Process frames in batches (future enhancement)
- Use smaller model variants (osnet_x0_5 instead of osnet_x1_0)
- Reduce MAX_PERSONS_PER_FRAME for faster processing
- Disable demographics detection if not needed

### Troubleshooting

**Models not downloading:**
- Check internet connection
- Check disk space (need ~500 MB free)
- Check `models_cache/` directory permissions
- Check firewall settings (allow Hugging Face, PyTorch Hub)
- Manually download models and place in `models_cache/`

**ChromaDB connection failed:**
- Verify ChromaDB service is running: `docker-compose ps chromadb`
- Check ChromaDB health: `curl http://localhost:8000/api/v1/heartbeat`
- Check network connectivity to ChromaDB
- Verify CHROMADB_HOST and CHROMADB_PORT in .env

**Low detection accuracy:**
- Increase PERSON_DETECTION_CONFIDENCE (default 0.5)
- Increase FACE_DETECTION_CONFIDENCE (default 0.9)
- Check video quality (resolution, lighting)
- Verify models loaded correctly (check logs)

**ReID not matching persons:**
- Lower REID_SIMILARITY_THRESHOLD (default 0.8)
- Check if persons have significant appearance changes (clothing, angle)
- Verify OSNet embeddings are being stored in ChromaDB
- Check time_window_hours is appropriate

**GPU not being used:**
- Verify CUDA is installed: `python -c "import torch; print(torch.cuda.is_available())"`
- Set USE_GPU_INFERENCE=true in .env
- Check GPU memory (need ~2 GB free)
- Install GPU-compatible PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

### Integration with Other Modules

**Used by:**
- AI Orchestrator (Phase 12) - calls `detect_persons()` for each frame
- Report Service (Phase 11) - calls `find_similar_persons()` for incident reports
- Ticket Service (Phase 9) - links persons to tickets via `ticket_persons` association

**Uses:**
- VideoProcessorService - for frame extraction
- StorageService - for saving person thumbnails
- ChromaDBManager - for embedding storage and search
- ModelManager - for model downloads and caching

**Database Integration:**
- Person records stored in MySQL with TTL (2 hours)
- Embeddings stored in ChromaDB with matching TTL
- SQLAlchemy events automatically clear TTL when person linked to ticket
- Cleanup task deletes expired persons and embeddings every 15 minutes

## AI Modules: Scene Understanding & Object Detection

### Overview

VigilentEye uses advanced AI models for scene understanding and object detection to provide environmental context and identify suspicious items in surveillance footage.

### Scene Analysis Module

**Features:**
- **Scene Classification**: Indoor vs outdoor detection
- **Lighting Analysis**: Bright, dim, dark, night classification
- **Weather Detection**: Clear, rainy, foggy, snowy conditions
- **Crowd Density**: Empty, sparse, moderate, crowded estimation
- **Detailed Descriptions**: Natural language scene captions using BLIP-2
- **Location Type**: Parking lot, street, building, park classification
- **Time of Day**: Day, night, dawn, dusk estimation

**AI Model: BLIP-2 (Bootstrapping Language-Image Pre-training)**
- **Model**: Salesforce/blip2-opt-2.7b
- **Size**: ~5 GB (configurable to use smaller blip-base ~1GB)
- **Speed**: ~500ms per frame (GPU), ~2s (CPU)
- **License**: BSD-3-Clause (open source)
- **Capabilities**: Generates detailed natural language descriptions of images

**Usage:**
```python
from src.ai_modules import SceneAnalyzerService

scene_analyzer = SceneAnalyzerService()

# Analyze scene in a frame
scene_data, error = scene_analyzer.analyze_scene(frame)

# Returns:
# {
#   'scene_type': 'outdoor',
#   'lighting': 'dim',
#   'weather': 'clear',
#   'crowd_density': 'sparse',
#   'description': 'An outdoor parking lot at night with dim lighting and few people',
#   'environment_details': {
#     'location_type': 'parking_lot',
#     'time_of_day': 'night',
#     'visibility': 'poor'
#   },
#   'confidence': 0.85
# }
```

**Fallback Mode:**
- If BLIP-2 unavailable, uses rule-based analysis:
  - Brightness analysis for lighting classification
  - Edge detection for indoor/outdoor estimation
  - Lower confidence scores (~0.5)
  - Enabled via `USE_SCENE_FALLBACK=true`

### Object Detection Module

**Features:**
- **Object Detection**: Detect 80 COCO object classes using YOLOv8
- **Threat Classification**: Classify objects by threat level (high, medium, low, none)
- **Suspicious Items Focus**: Weapons, tools, bags, vehicles
- **Object-Person Relationships**: Detect who's holding what using IoU
- **Threat Summary**: Aggregate threat assessment for the frame

**AI Model: YOLOv8-nano**
- **Reuses existing model** from PersonDetector (no additional download)
- **Detects**: All 80 COCO classes (persons, vehicles, objects, etc.)
- **Speed**: ~50ms per frame (GPU), ~200ms (CPU)
- **License**: AGPL-3.0

**Threat Level Mappings:**

**High Threat (Weapons):**
- Knife (class 43)
- Scissors (class 76)
- Baseball bat (class 37)

**Medium Threat (Tools/Bags):**
- Backpack (class 24)
- Handbag (class 26)
- Suitcase (class 28)
- Umbrella (class 25)

**Low Threat (Common Items):**
- Bottle (class 39)
- Cell phone (class 67)
- Laptop (class 63)

**Vehicles:**
- Car, motorcycle, bus, truck (classes 2, 3, 5, 7)

**Usage:**
```python
from src.ai_modules import ObjectDetectorService

object_detector = ObjectDetectorService()

# Detect objects (standalone)
objects_data, error = object_detector.detect_objects(frame)

# Detect objects with person relationships
objects_data, error = object_detector.detect_objects(frame, person_detections)

# Returns:
# {
#   'objects': [
#     {
#       'object_id': 'obj_uuid',
#       'class_id': 43,
#       'class_name': 'knife',
#       'bbox': [100, 100, 150, 150],
#       'confidence': 0.92,
#       'threat_level': 'high',
#       'category': 'weapon'
#     }
#   ],
#   'relationships': [
#     {
#       'person_id': 'person_uuid',
#       'object_id': 'obj_uuid',
#       'relationship': 'holding',
#       'confidence': 0.88,
#       'spatial_proximity': 'high'
#     }
#   ],
#   'threat_summary': {
#     'max_threat_level': 'high',
#     'high_threat_count': 1,
#     'medium_threat_count': 0,
#     'low_threat_count': 0,
#     'total_objects': 1
#   }
# }
```

**Object-Person Relationship Detection:**

**How it works:**
1. Calculate IoU (Intersection over Union) between object and person bounding boxes
2. Classify relationship based on IoU:
   - **IoU > 0.3**: 'holding' (high spatial proximity)
   - **IoU > 0.1**: 'near' (medium spatial proximity)
   - **Distance < 100px**: 'in_vicinity' (low spatial proximity)
3. Return relationship with confidence score (IoU value)

**Use Cases:**
- Detect "person holding weapon" (critical threat)
- Detect "person with suspicious bag" (medium threat)
- Track object ownership across frames
- Provide context for LLM analysis

## AI Modules: Audio Processing (Speech-to-Text & Audio Classification)

### Overview

VigilentEye processes audio from surveillance footage using two AI modules: speech-to-text transcription with threat keyword detection, and audio event classification for detecting suspicious sounds.

### Speech-to-Text Module

**Features:**
- **Transcription**: Convert speech to text using OpenAI Whisper
- **Language Detection**: Auto-detect 99 languages
- **Noise Reduction**: Preprocessing to improve transcription accuracy
- **Speaker Diarization**: Simple energy-based speaker change detection
- **Threat Keywords**: Detect keywords like 'gun', 'help', 'fire', 'weapon'
- **Profanity Detection**: Optional profanity keyword matching
- **Word Timestamps**: Precise timing for each word/segment

**AI Model: OpenAI Whisper**
- **Model**: base (74M parameters)
- **Size**: ~140 MB
- **Speed**: ~1x realtime (30s audio = 30s on CPU, 5s on GPU)
- **Languages**: 99 languages with auto-detection
- **License**: MIT (open source)
- **Accuracy**: High accuracy even with accents and background noise

**Usage:**
```python
from src.ai_modules import SpeechToTextService

speech_to_text = SpeechToTextService()

# Transcribe audio file
transcription_data, error = speech_to_text.transcribe_audio(audio_path)

# Returns:
# {
#   'transcription': 'I heard a gunshot and someone yelling for help',
#   'language': 'en',
#   'language_confidence': 0.95,
#   'segments': [
#     {'text': 'I heard a gunshot', 'start': 0.0, 'end': 2.5, 'speaker_id': 1},
#     {'text': 'and someone yelling for help', 'start': 2.5, 'end': 5.0, 'speaker_id': 2}
#   ],
#   'threat_keywords': ['gun', 'help'],
#   'profanity_detected': False,
#   'profanity_keywords': [],
#   'confidence': 0.88
# }
```

**Noise Reduction:**
- High-pass filter using `librosa.effects.preemphasis()`
- Silence trimming using `librosa.effects.trim()`
- Audio normalization for consistent volume
- Improves transcription accuracy by 10-20%

**Speaker Diarization:**
- **Current**: Simple energy-based approach
  - Detects silence gaps in audio
  - Assumes speaker changes at silence boundaries
  - Assigns sequential speaker IDs
  - Accuracy: ~60-70% (basic heuristic)
- **Future Enhancement**: Use pyannote.audio for ML-based diarization
  - Accuracy: ~90%+ (industry standard)
  - Requires additional ~500MB models
  - Document as optional enhancement

**Threat Keyword Detection:**
- Case-insensitive whole-word matching
- Default keywords: gun, shoot, kill, bomb, help, fire, weapon, attack, knife, threat
- Configurable via `THREAT_KEYWORDS` environment variable
- Returns matched keywords with context

### Audio Classification Module

**Features:**
- **Audio Event Detection**: Detect 521 audio event classes using YAMNet
- **Urgency Classification**: Classify sounds by urgency (critical, high, medium, low)
- **Suspicious Sounds Focus**: Gunshots, screams, alarms, glass breaking, sirens
- **Temporal Localization**: Timestamp for each detected sound (0.96s segments)
- **Ambient Noise Analysis**: Estimate background noise level
- **Urgency Summary**: Aggregate urgency assessment for the audio

**AI Model: YAMNet (Yet Another Mobile Network)**
- **Model**: Google's YAMNet from TensorFlow Hub
- **Size**: ~5 MB (very lightweight)
- **Speed**: ~100x realtime (30s audio = 0.3s processing)
- **Classes**: 521 audio event classes from AudioSet ontology
- **License**: Apache 2.0 (open source)
- **Accuracy**: High accuracy on AudioSet evaluation set

**Usage:**
```python
from src.ai_modules import AudioClassifierService

audio_classifier = AudioClassifierService()

# Classify audio events
audio_data, error = audio_classifier.classify_audio(audio_path)

# Returns:
# {
#   'detected_sounds': [
#     {
#       'sound_id': 'sound_uuid',
#       'class_name': 'Gunshot, gunfire',
#       'category': 'violence',
#       'urgency_level': 'critical',
#       'confidence': 0.92,
#       'timestamp': 12.5,
#       'duration': 0.96
#     },
#     {
#       'sound_id': 'sound_uuid',
#       'class_name': 'Alarm',
#       'category': 'alert',
#       'urgency_level': 'high',
#       'confidence': 0.85,
#       'timestamp': 15.2,
#       'duration': 0.96
#     }
#   ],
#   'urgency_summary': {
#     'max_urgency': 'critical',
#     'critical_count': 1,
#     'high_count': 1,
#     'medium_count': 0,
#     'low_count': 0,
#     'total_sounds': 2
#   },
#   'ambient_noise_level': 'moderate',
#   'confidence': 0.88
# }
```

**Urgency Level Mappings:**

**Critical Urgency (Immediate Response Required):**
- Gunshot, gunfire
- Explosion
- Screaming

**High Urgency (Urgent Response Required):**
- Alarm, fire alarm
- Siren (emergency vehicle, civil defense)
- Glass breaking, crash
- Yelling, shouting

**Medium Urgency (Attention Required):**
- Dog barking (aggressive)
- Car horn (prolonged)
- Door slamming
- Running footsteps

**Low Urgency (Informational):**
- Music
- Speech (normal conversation)
- Ambient noise
- Vehicle sounds (normal traffic)

**YAMNet Audio Classes:**

YAMNet detects 521 classes from AudioSet ontology including:
- **Violence**: Gunshot, explosion, fighting, screaming
- **Alarms**: Fire alarm, smoke detector, car alarm, siren
- **Breaking**: Glass breaking, crash, smash
- **Human**: Speech, laughter, crying, yelling, screaming, coughing
- **Animals**: Dog barking, cat meowing, bird chirping
- **Vehicles**: Car, motorcycle, truck, siren, horn
- **Environmental**: Thunder, rain, wind, fire
- **Music**: Various instruments and genres

### Audio Processing Pipeline

**End-to-End Flow:**
1. Video uploaded or streamed
2. VideoProcessorService extracts audio using FFmpeg/pydub
3. Audio saved to `storage/audio/` directory
4. SpeechToTextService transcribes audio (parallel with video AI)
5. AudioClassifierService detects audio events (parallel with video AI)
6. Outputs aggregated by AI Orchestrator
7. LLM analyzes combined outputs for threat assessment
8. If suspicious, audio stored as evidence

**Audio Preprocessing:**
- Load audio with librosa (16kHz sample rate)
- Convert to mono if stereo
- Apply noise reduction (high-pass filter, silence trimming)
- Normalize amplitude
- Feed to Whisper and YAMNet

**Supported Audio Formats:**
- WAV (recommended)
- MP3
- FLAC
- OGG
- M4A
- Any format supported by librosa/soundfile

### Configuration

**Environment Variables:**
```env
# Scene Analysis
SCENE_CONFIDENCE_THRESHOLD=0.7
BLIP2_MODEL_NAME=Salesforce/blip2-opt-2.7b
BLIP2_MAX_LENGTH=100
USE_SCENE_FALLBACK=true

# Object Detection
OBJECT_DETECTION_CONFIDENCE=0.5
OBJECT_MIN_SIZE=30
MAX_OBJECTS_PER_FRAME=100
OBJECT_PERSON_IOU_THRESHOLD=0.1
DETECT_ALL_OBJECTS=false

# Speech-to-Text
WHISPER_MODEL_SIZE=base                    # tiny|base|small|medium|large
TRANSCRIPTION_CONFIDENCE_THRESHOLD=0.7
ENABLE_NOISE_REDUCTION=true
ENABLE_SPEAKER_DIARIZATION=true
THREAT_KEYWORDS=gun,shoot,kill,bomb,help,fire,weapon,attack,knife,threat
PROFANITY_KEYWORDS=                        # Optional, empty by default

# Audio Classification
AUDIO_CLASSIFICATION_CONFIDENCE=0.5
MAX_SOUNDS_PER_SEGMENT=5
YAMNET_MODEL_URL=https://tfhub.dev/google/yamnet/1
```

**Model Downloads:**

**First Run:**
- BLIP-2: ~5 GB download (2-5 minutes)
- YOLOv8: Already cached from PersonDetector (no additional download)
- Whisper base: ~140 MB download (30-60 seconds)
- YAMNet: ~5 MB download (5-10 seconds)
- Total new download: ~5.15 GB

**Subsequent Runs:**
- Models loaded from `models_cache/` (instant)
- No network requests needed

**Model Locations:**
```
models_cache/
├── yolov8/yolov8n.pt          (~6 MB, shared with PersonDetector)
├── blip2/                     (~5 GB, new for SceneAnalyzer)
├── whisper/base.pt            (~140 MB, new for SpeechToText)
└── yamnet/model.h5            (~5 MB, new for AudioClassifier)
```

### Performance Considerations

**Inference Speed (per frame):**
- Scene Analysis (BLIP-2): ~500ms (GPU), ~2s (CPU)
- Object Detection (YOLOv8): ~50ms (GPU), ~200ms (CPU)
- Relationship Detection: ~1ms per object-person pair
- **Total for typical frame**: ~600ms (GPU), ~2.5s (CPU)

**Inference Speed (per 30s audio):**
- Speech-to-Text (Whisper): ~30s (CPU), ~5s (GPU)
- Audio Classification (YAMNet): ~0.3s (CPU/GPU)
- Noise reduction: ~10ms
- **Total audio processing**: ~30-35s (CPU), ~5-10s (GPU)

**Memory Usage:**
- BLIP-2: ~6 GB VRAM (GPU) or ~8 GB RAM (CPU)
- YOLOv8: ~500 MB (shared with PersonDetector)
- Whisper base: ~1 GB RAM
- YAMNet: ~500 MB RAM
- Audio buffer: ~100 MB for 30s audio

## AI Module: LLM Threat Analyzer

### Overview

The LLM Analyzer is the final AI component that aggregates outputs from all 5 detection modules (Person, Scene, Object, Speech, Audio) and performs intelligent threat assessment using a locally-hosted large language model via Ollama.

### Features

- **Multi-Modal Analysis**: Combines vision and audio AI outputs for comprehensive threat assessment
- **Local LLM Inference**: Uses Ollama for privacy-preserving, cost-free analysis
- **Structured Output**: Enforces JSON schema with Pydantic validation
- **Few-Shot Learning**: Includes 3-5 example analyses for better accuracy
- **Chain-of-Thought Reasoning**: Step-by-step reasoning for explainability
- **Confidence Thresholding**: Only flags as suspicious if confidence ≥ 0.7 (configurable)
- **Rule-Based Fallback**: Simple heuristics if LLM unavailable
- **Retry Logic**: Automatic retry with schema hints if JSON parsing fails

### AI Model: Llama 3.2 or Phi-3 Mini

**Default: Llama 3.2 1B**
- **Size**: ~1.3 GB
- **Speed**: ~500ms per analysis (CPU), ~100ms (GPU)
- **Context**: 128k tokens (more than enough for our prompts)
- **License**: Llama 3.2 Community License (free for commercial use)
- **Strengths**: Fast, lightweight, good reasoning for simple tasks

**Alternative: Phi-3 Mini (3.8B)**
- **Size**: ~2.3 GB
- **Speed**: ~1s per analysis (CPU), ~200ms (GPU)
- **Context**: 128k tokens
- **License**: MIT (fully open source)
- **Strengths**: Better reasoning, more accurate, handles complex scenarios

**Model Selection:**
Configurable via `OLLAMA_MODEL` environment variable:
- `llama3.2:1b` - Default, fastest
- `llama3.2:3b` - More accurate, slower
- `phi3:mini` - Best reasoning, moderate speed
- `phi3:medium` - Highest accuracy, slowest

### Usage

```python
from src.ai_modules import LLMAnalyzerService

llm_analyzer = LLMAnalyzerService()

# Aggregate outputs from all 5 AI modules
ai_outputs = {
    'scene': scene_data,  # From SceneAnalyzerService
    'persons': person_detections,  # From PersonDetectorService
    'objects': objects_data,  # From ObjectDetectorService
    'transcription': transcription_data,  # From SpeechToTextService
    'audio_events': audio_events_data,  # From AudioClassifierService
}

# Analyze situation
analysis, error = llm_analyzer.analyze_situation(
    ai_outputs=ai_outputs,
    timestamp=datetime.utcnow(),
    location='Parking Lot Camera 3'
)

# Returns:
# {
#   'is_suspicious': True,
#   'confidence': 0.92,
#   'threat_level': 'high',
#   'reasoning': 'The situation is suspicious because: 1) A person is detected holding a knife (high-threat weapon), 2) Glass breaking sound was heard indicating potential break-in, 3) The scene is at night with poor lighting which is unusual for this location. These factors combined suggest a potential security threat.',
#   'recommended_action': 'alert',
#   'key_factors': [
#     'Person holding weapon (knife)',
#     'Glass breaking sound detected',
#     'Night time with poor lighting',
#     'High threat object detected'
#   ]
# }
```

### Prompt Engineering

**Prompt Structure:**

1. **System Instruction**:
   - "You are a security analysis AI for a surveillance system."
   - "Analyze the following situation and determine if it's suspicious."
   - "Respond ONLY with valid JSON matching the schema."

2. **Few-Shot Examples** (if enabled):
   - 3-5 example analyses with inputs and expected outputs
   - Covers suspicious and non-suspicious scenarios
   - Includes edge cases (context matters)

3. **Chain-of-Thought Instruction** (if enabled):
   - "Let's analyze this step by step:"
   - Encourages LLM to show reasoning process
   - Improves accuracy by 15-20%

4. **Current Situation**:
   - TIME: ISO timestamp
   - LOCATION: Camera location
   - SCENE: Environment description, lighting, weather, crowd
   - PEOPLE: Count, demographics, clothing, actions
   - OBJECTS: Detected objects with threat levels, relationships
   - AUDIO TRANSCRIPTION: Speech text, threat keywords
   - AUDIO EVENTS: Detected sounds with urgency levels

5. **Output Schema**:
   - JSON schema definition with field descriptions
   - Constraints: confidence 0.0-1.0, threat_level enum, etc.

6. **Final Instruction**:
   - "Based on this information, assess if this situation is suspicious."
   - "Respond ONLY with valid JSON."

**Example Prompt (Abbreviated):**

```
You are a security analysis AI. Analyze the following situation:

TIME: 2024-01-15T22:30:00Z
LOCATION: Parking Lot Camera 3
SCENE: Outdoor parking lot at night with dim lighting, sparse crowd
PEOPLE: 2 persons detected. Person 1: male, age 25, dark clothing. Person 2: male, age 30, dark jacket.
OBJECTS: 1 high-threat object detected (knife). Person 1 is holding the knife.
AUDIO TRANSCRIPTION: "[glass breaking sound]" Threat keywords: none
AUDIO EVENTS: Glass breaking (urgency: high, confidence: 0.92), Yelling (urgency: high, confidence: 0.78)

Respond with JSON: {is_suspicious, confidence, threat_level, reasoning, recommended_action, key_factors}
```

### Structured Output Validation

**Pydantic Schema:**

```python
class SuspicionAnalysis(BaseModel):
    is_suspicious: bool
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0-1.0 range
    threat_level: str = Field(pattern='^(low|medium|high|critical)$')  # Enum validation
    reasoning: str = Field(min_length=10)  # Require detailed reasoning
    recommended_action: str = Field(pattern='^(alert|monitor|escalate|ignore)$')
    key_factors: List[str] = Field(min_items=1, max_items=10)  # 1-10 factors
```

**Validation Process:**
1. LLM generates JSON response
2. Parse JSON with `json.loads()`
3. Validate with Pydantic: `SuspicionAnalysis.model_validate(data)`
4. If validation fails, retry with schema hints in prompt
5. If all retries fail, use rule-based fallback

**Benefits:**
- Ensures consistent output format
- Catches LLM hallucinations (invalid values)
- Provides clear error messages for debugging
- Enables type-safe consumption by orchestrator

### Rule-Based Fallback

**When Used:**
- Ollama service unavailable
- LLM returns invalid JSON after max retries
- LLM timeout or error
- Enabled via `ENABLE_RULE_BASED_FALLBACK=true`

**Fallback Logic:**

```python
if any(obj['threat_level'] == 'high' for obj in objects):
    is_suspicious = True
    threat_level = 'high'
elif any(sound['urgency_level'] == 'critical' for sound in audio_events):
    is_suspicious = True
    threat_level = 'critical'
elif threat_keywords in transcription:
    is_suspicious = True
    threat_level = 'medium'
else:
    is_suspicious = False
    threat_level = 'low'
```

**Confidence:**
- Fallback analysis has confidence=0.6 (lower than LLM)
- Indicates less reliable assessment
- Still useful for basic threat detection

### Configuration

**Environment Variables:**

```env
# Ollama Service
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# LLM Analyzer
LLM_CONFIDENCE_THRESHOLD=0.7
LLM_MAX_TOKENS=500
LLM_TEMPERATURE=0.3
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
USE_CHAIN_OF_THOUGHT=true
USE_FEW_SHOT_EXAMPLES=true
ENABLE_RULE_BASED_FALLBACK=true
```

**Model Download:**

**First Run:**
- Llama 3.2 1B: ~1.3 GB download (1-2 minutes)
- Phi-3 Mini: ~2.3 GB download (2-3 minutes)
- Downloaded via Ollama API: `ollama pull llama3.2:1b`
- Cached in Docker volume: `ollama_data:/root/.ollama`

**Subsequent Runs:**
- Model loaded from Ollama cache (instant)
- No network requests needed
- Ollama handles model management automatically

### Performance Considerations

**Inference Speed:**
- Llama 3.2 1B: ~500ms (CPU), ~100ms (GPU)
- Phi-3 Mini: ~1s (CPU), ~200ms (GPU)
- Prompt processing: ~50ms
- JSON parsing: ~10ms
- **Total per analysis**: ~600ms (CPU), ~200ms (GPU)

**Memory Usage:**
- Llama 3.2 1B: ~4 GB RAM
- Phi-3 Mini: ~8 GB RAM
- Ollama service manages memory automatically
- Models stay loaded in memory for fast inference

**Optimization Tips:**
- Use Llama 3.2 1B for fastest inference (recommended)
- Use GPU for 4-5x speedup
- Reduce `LLM_MAX_TOKENS` for faster generation
- Disable few-shot examples for faster prompts (slight accuracy loss)
- Use lower temperature (0.1-0.2) for more deterministic outputs

### Troubleshooting

**Ollama service not running:**
- Check Docker: `docker-compose ps ollama`
- Start service: `docker-compose up -d ollama`
- Check logs: `docker-compose logs ollama`
- Verify health: `curl http://localhost:11434/api/tags`

**Model download fails:**
- Check internet connection
- Check disk space (need ~2-5 GB free)
- Manually pull model: `docker exec vigilanteye-ollama ollama pull llama3.2:1b`
- Try alternative model: `OLLAMA_MODEL=phi3:mini`

**LLM returns invalid JSON:**
- Check LLM_TEMPERATURE (lower = more structured)
- Enable retries: `LLM_MAX_RETRIES=3`
- Check prompt format (ensure schema is clear)
- Use fallback: `ENABLE_RULE_BASED_FALLBACK=true`

**LLM analysis is inaccurate:**
- Use larger model: `OLLAMA_MODEL=llama3.2:3b` or `phi3:mini`
- Enable few-shot examples: `USE_FEW_SHOT_EXAMPLES=true`
- Enable chain-of-thought: `USE_CHAIN_OF_THOUGHT=true`
- Lower temperature: `LLM_TEMPERATURE=0.1` (more deterministic)
- Review and improve few-shot examples in code

**LLM timeout:**
- Increase timeout: `LLM_TIMEOUT_SECONDS=60`
- Use smaller model: `OLLAMA_MODEL=llama3.2:1b`
- Reduce max tokens: `LLM_MAX_TOKENS=300`
- Check Ollama service resources (CPU/RAM)

**Confidence too low:**
- Lower threshold: `LLM_CONFIDENCE_THRESHOLD=0.5`
- Use larger model for better confidence calibration
- Review prompt clarity (ambiguous prompts = lower confidence)

**Out of memory:**
- Ollama requires 4-8 GB RAM depending on model
- Use smaller model: `llama3.2:1b` (4GB) instead of `phi3:medium` (16GB)
- Allocate more memory to Docker
- Close other applications

### Integration with Other Modules

**Receives Input From:**
- PersonDetectorService - person detections with demographics
- SceneAnalyzerService - scene understanding and context
- ObjectDetectorService - object detections with threat levels
- SpeechToTextService - transcription with threat keywords
- AudioClassifierService - audio events with urgency levels

**Provides Output To:**
- AI Orchestrator (Phase 12) - final threat assessment
- Ticket Service (Phase 9) - creates ticket if suspicious
- Messenger Service (Phase 10) - sends alert if suspicious
- Report Service (Phase 11) - includes LLM reasoning in reports
- Evidence storage - stores analysis in Evidence.ai_analysis JSON column

**Decision Flow:**

```
All 5 AI modules → LLMAnalyzerService → {is_suspicious, threat_level, reasoning}
  ↓
if is_suspicious AND confidence ≥ threshold:
  → Create Ticket
  → Send Telegram Alert
  → Store Evidence
  → Generate Report
else:
  → Mark as Clean
  → Show Notification
  → No Action
```

### Example Scenarios

**Scenario 1: Suspicious - Weapon Detected**

**Input:**
- Scene: Outdoor parking lot, night, dim lighting
- Persons: 1 male, age 25, dark clothing
- Objects: Knife (high threat), person holding knife
- Transcription: None (no speech)
- Audio: Glass breaking (high urgency)

**LLM Output:**
```json
{
  "is_suspicious": true,
  "confidence": 0.92,
  "threat_level": "high",
  "reasoning": "This situation is highly suspicious. A person is detected holding a knife (high-threat weapon) in a parking lot at night with poor lighting. Additionally, glass breaking sounds were detected, suggesting a potential break-in or vandalism. The combination of weapon possession, suspicious timing (night), and breaking sounds indicates a likely security threat.",
  "recommended_action": "alert",
  "key_factors": [
    "Person holding weapon (knife)",
    "Glass breaking sound detected",
    "Night time with poor lighting",
    "Outdoor parking lot (vulnerable location)"
  ]
}
```

**Scenario 2: Not Suspicious - Normal Activity**

**Input:**
- Scene: Indoor office, bright lighting, day
- Persons: 3 persons, mixed demographics, business attire
- Objects: Laptops, phones (low threat)
- Transcription: "Let's review the quarterly report"
- Audio: Normal speech, keyboard typing

**LLM Output:**
```json
{
  "is_suspicious": false,
  "confidence": 0.88,
  "threat_level": "low",
  "reasoning": "This situation shows normal office activity. Multiple persons are present in a well-lit indoor environment during daytime. The detected objects (laptops, phones) are typical office equipment. The transcription indicates a business meeting ('quarterly report'). No threat indicators, weapons, or suspicious sounds detected. This is routine workplace activity.",
  "recommended_action": "ignore",
  "key_factors": [
    "Indoor office environment",
    "Daytime with good lighting",
    "Normal business conversation",
    "No threat indicators detected"
  ]
}
```

**Scenario 3: Suspicious - Audio Threat**

**Input:**
- Scene: Outdoor street, night, moderate crowd
- Persons: 5 persons, various demographics
- Objects: No suspicious objects
- Transcription: "Help! Someone call 911!"
- Audio: Screaming (critical urgency), gunshot (critical urgency)

**LLM Output:**
```json
{
  "is_suspicious": true,
  "confidence": 0.95,
  "threat_level": "critical",
  "reasoning": "This is a critical security situation. Gunshot sounds were detected (critical urgency), along with screaming and a distress call for emergency services ('Help! Someone call 911!'). The audio evidence strongly indicates an active violent incident. Immediate response is required.",
  "recommended_action": "escalate",
  "key_factors": [
    "Gunshot detected (critical audio event)",
    "Screaming and distress calls",
    "Emergency services requested (911)",
    "Multiple persons present (potential victims)"
  ]
}
```

### Confidence Thresholding

**How it works:**
- LLM returns confidence score (0.0-1.0)
- Compare to threshold (default 0.7)
- If `confidence < threshold`, override `is_suspicious = False`
- Prevents false positives from low-confidence assessments

**Threshold Guidelines:**
- **0.5**: Sensitive (more false positives, fewer false negatives)
- **0.7**: Balanced (recommended for most scenarios)
- **0.9**: Conservative (fewer false positives, more false negatives)

**Adjusting Threshold:**
- High-security areas: Use 0.5 (catch more potential threats)
- Low-risk areas: Use 0.9 (reduce alert fatigue)
- Configure per camera or globally via `LLM_CONFIDENCE_THRESHOLD`

### Ollama Service Setup

**Docker Compose:**

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: vigilanteye-ollama
  restart: unless-stopped
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  networks:
    - vigilanteye-network
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Starting Ollama:**

```bash
# Start Ollama service
docker-compose up -d ollama

# Pull model manually (optional, auto-pulled on first use)
docker exec vigilanteye-ollama ollama pull llama3.2:1b

# List available models
docker exec vigilanteye-ollama ollama list

# Test inference
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Is this suspicious: person with knife at night?",
  "stream": false
}'
```

**Model Management:**

```bash
# Pull different model
docker exec vigilanteye-ollama ollama pull phi3:mini

# Remove model to free space
docker exec vigilanteye-ollama ollama rm llama3.2:1b

# Check model info
docker exec vigilanteye-ollama ollama show llama3.2:1b
```

### Integration Example

**Complete AI Pipeline:**

```python
# Step 1: Extract frames and audio from video
frames = video_processor.extract_frames(video_path)
audio_path = video_processor.extract_audio(video_path)

# Step 2: Run 5 AI modules in parallel (handled by orchestrator)
persons, _ = person_detector.detect_persons(frame, video_id, timestamp, frame_num)
scene, _ = scene_analyzer.analyze_scene(frame)
objects, _ = object_detector.detect_objects(frame, persons)
transcription, _ = speech_to_text.transcribe_audio(audio_path)
audio_events, _ = audio_classifier.classify_audio(audio_path)

# Step 3: Aggregate outputs
ai_outputs = {
    'scene': scene,
    'persons': persons,
    'objects': objects,
    'transcription': transcription,
    'audio_events': audio_events,
}

# Step 4: LLM analysis (final step)
analysis, _ = llm_analyzer.analyze_situation(ai_outputs, timestamp, location)

# Step 5: Decision making
if analysis['is_suspicious'] and analysis['confidence'] >= 0.7:
    # Create ticket, send alert, store evidence
    ticket = ticket_service.create_ticket(video_id, analysis)
    messenger_service.send_alert(ticket, analysis)
    storage_service.save_evidence(frame, audio, ticket_id)
else:
    # Mark as clean, no action
    video.mark_analyzed('clean')
```

## AI Pipeline Summary

**All 6 AI Modules:**

1. **PersonDetectorService** - Detect and track persons with ReID
2. **SceneAnalyzerService** - Understand environment and context
3. **ObjectDetectorService** - Detect suspicious objects and relationships
4. **SpeechToTextService** - Transcribe speech and detect threat keywords
5. **AudioClassifierService** - Classify audio events by urgency
6. **LLMAnalyzerService** - Aggregate and analyze for threat assessment

**Total Model Size:** ~7 GB (all models combined)
**Total Inference Time:** ~3-4s per frame (CPU), ~1s (GPU)
**Cost:** $0 (all models run locally)

**Processing Flow:**
Video → Extract Frames + Audio → Parallel AI (5 modules) → LLM Aggregation → Threat Decision → Action (Alert/Ignore)

## Ticket Management System

### Overview

VigilentEye's ticket management system tracks security incidents from detection through resolution. The system includes automated workflows (auto-escalation, auto-close), SLA tracking, and comprehensive audit trails.

### Features

- **Ticket Lifecycle Management**: Create, acknowledge, close, escalate tickets
- **State Machine**: Enforced state transitions (OPEN → ACKNOWLEDGED → IN_PROGRESS → RESOLVED → CLOSED)
- **Auto-Escalation**: Unacknowledged tickets escalate after 15 minutes
- **Auto-Close**: Tickets automatically close after 2 hours (configurable)
- **SLA Tracking**: Monitor response time and resolution time
- **Evidence Linking**: Link tickets to video frames, audio, and person detections
- **Audit Trail**: Complete history of all ticket state changes
- **Role-Based Access**: Staff see assigned tickets, admins see all tickets

### TicketService

**Core ticket management operations:**

```python
from src.services import TicketService

ticket_service = TicketService()

# Create ticket from AI analysis
ticket, error = ticket_service.create_ticket(
    video_id=video.id,
    analysis_result=llm_analysis,  # From LLMAnalyzerService
    evidence_ids=[evidence1.id, evidence2.id],
    person_ids=[person1.id, person2.id],
    created_by_user_id=None  # System-generated
)

# Acknowledge ticket
ticket, error = ticket_service.acknowledge_ticket(
    ticket_id=ticket.id,
    user_id=staff_user.id
)

# Close ticket
ticket, error = ticket_service.close_ticket(
    ticket_id=ticket.id,
    user_id=staff_user.id,
    reason='Issue resolved, suspect apprehended'
)

# Escalate ticket
ticket, error = ticket_service.escalate_ticket(
    ticket_id=ticket.id,
    reason='No response from first responders'
)

# Get ticket details
ticket_dict, error = ticket_service.get_ticket_details(
    ticket_id=ticket.id,
    user_id=user.id,
    user_role=user.role
)

# List tickets with filters
result, error = ticket_service.list_tickets(
    filters={'status': 'open', 'priority': 'high'},
    page=1,
    per_page=20,
    user_id=user.id,
    user_role=user.role
)
```

### API Endpoints

All ticket endpoints are available at `/api/tickets/*`:

#### List Tickets

**GET /api/tickets**

- List tickets with pagination and filtering
- Headers: `Authorization: Bearer <access_token>`
- Query params: `page`, `per_page`, `status`, `priority`, `assigned_to`, `date_from`, `date_to`, `threat_level`
- Response: `{"tickets": [...], "pagination": {...}}`
- Staff users see only assigned tickets; admins see all tickets

#### Get Ticket Details

**GET /api/tickets/{ticket_id}**

- Get detailed ticket information with evidence, persons, and history
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"ticket": {"id": "uuid", "title": "...", "status": "open", "evidence": [...], "persons_of_interest": [...], "history": [...]}}`
- Staff can only view assigned tickets; admins can view any ticket

#### Create Ticket

**POST /api/tickets**

- Create new ticket (typically called by AI orchestrator)
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"video_id": "uuid", "analysis_result": {...}, "evidence_ids": [...], "person_ids": [...]}`
- Response: `{"message": "Ticket created successfully", "ticket": {...}}`
- Automatically sets auto_close_at (created_at + 2 hours)

#### Acknowledge Ticket

**POST /api/tickets/{ticket_id}/acknowledge**

- Acknowledge ticket and assign to current user
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"message": "Ticket acknowledged successfully", "ticket": {...}}`
- Checks SLA breach (> 15 minutes since creation)
- Creates history entry with response time

#### Close Ticket

**POST /api/tickets/{ticket_id}/close**

- Close ticket with optional reason
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"reason": "Issue resolved"}` (optional)
- Response: `{"message": "Ticket closed successfully", "ticket": {...}}`
- Creates history entry with resolution time

#### Escalate Ticket

**POST /api/tickets/{ticket_id}/escalate**

- Manually escalate ticket to secondary channel
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"reason": "No response from first responders"}` (optional)
- Response: `{"message": "Ticket escalated successfully", "ticket": {...}}`
- Sends alert to escalation Telegram channel (Phase 10)

#### Update Status

**PATCH /api/tickets/{ticket_id}/status**

- Update ticket status with state machine validation
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"status": "in_progress"}`
- Response: `{"message": "Ticket status updated successfully", "ticket": {...}}`
- Validates state transition before updating

#### Assign Ticket

**PATCH /api/tickets/{ticket_id}/assign**

- Assign ticket to user
- Headers: `Authorization: Bearer <access_token>`
- Request: `{"user_id": "uuid"}`
- Response: `{"message": "Ticket assigned successfully", "ticket": {...}}`
- Staff can only assign to themselves; admins can assign to anyone

### Ticket State Machine

**Valid State Transitions:**

```
OPEN → ACKNOWLEDGED
OPEN → CLOSED (auto-close or manual)
ACKNOWLEDGED → IN_PROGRESS
ACKNOWLEDGED → CLOSED
IN_PROGRESS → RESOLVED
IN_PROGRESS → CLOSED
RESOLVED → CLOSED
```

**Invalid Transitions:**

- CLOSED → any state (tickets cannot be reopened)
- ACKNOWLEDGED → OPEN (cannot un-acknowledge)
- Any backward transition (state machine is forward-only)

**State Descriptions:**

- **OPEN**: Ticket created, awaiting acknowledgment
- **ACKNOWLEDGED**: First responder acknowledged, assigned to user
- **IN_PROGRESS**: Actively being investigated/resolved
- **RESOLVED**: Issue resolved, awaiting final closure
- **CLOSED**: Ticket closed, no further action needed

### Automated Workflows

**Auto-Escalation (Every 5 minutes):**

- Checks tickets with status=OPEN, not acknowledged, created > 15 minutes ago
- Sets sla_breach=True, escalated=True, increments escalation_count
- Sends alert to secondary Telegram channel (Phase 10)
- Creates TicketHistory entry with event='auto_escalated'
- Continues checking until ticket is acknowledged or closed

**Auto-Close (Every 10 minutes):**

- Checks tickets with auto_close_at < now, status != CLOSED
- Updates status to CLOSED, sets closed_at
- Creates TicketHistory entry with event='auto_closed'
- Tickets auto-close after 2 hours (configurable via `TICKET_AUTO_CLOSE_HOURS`)

**Celery Beat Schedule:**

- `check-ticket-escalations`: Every 5 minutes (300s)
- `auto-close-tickets`: Every 10 minutes (600s)
- `cleanup-expired-files`: Every 15 minutes (900s)

### SLA Tracking

**Metrics Tracked:**

- **Response Time**: Time from creation to acknowledgment
- **Resolution Time**: Time from creation to closure
- **SLA Breach**: True if not acknowledged within 15 minutes
- **Escalation Count**: Number of times ticket was escalated

**SLA Thresholds:**

- **Acknowledgment**: 15 minutes (configurable via `TICKET_ESCALATION_TIMEOUT_MINUTES`)
- **Auto-Close**: 2 hours (configurable via `TICKET_AUTO_CLOSE_HOURS`)

**Accessing SLA Metrics:**

```python
# Get response time
response_time = ticket.get_response_time()  # Seconds from creation to acknowledgment

# Get resolution time
resolution_time = ticket.get_resolution_time()  # Seconds from creation to closure

# Check SLA breach
if ticket.sla_breach:
    # Ticket was not acknowledged within 15 minutes
```

### Evidence and Person Linking

**Evidence Linking:**

- Evidence records have `ticket_id` foreign key
- When ticket created, evidence.ticket_id is set
- Evidence becomes permanent (TTL cleared) when linked to ticket
- Access via `ticket.evidence` relationship

**Person Linking:**

- Persons linked via `ticket_persons` association table
- Includes `relevance_score` (how relevant person is to incident)
- Includes `notes` (why person is linked)
- Access via `ticket.persons_of_interest` relationship
- Used for "persons of interest" in reports

**Example:**

```python
# Create ticket with evidence and persons
ticket, _ = ticket_service.create_ticket(
    video_id=video.id,
    analysis_result=llm_analysis,
    evidence_ids=[frame1.id, frame2.id, audio1.id],
    person_ids=[person1.id, person2.id]
)

# Access linked data
for evidence in ticket.evidence:
    print(f"Evidence: {evidence.type} at {evidence.timestamp}")

for person in ticket.persons_of_interest:
    print(f"Person: {person.age} {person.gender}, {person.clothing_description}")
```

### Configuration

**Environment Variables:**

```env
# Ticket Management
TICKET_ESCALATION_TIMEOUT_MINUTES=15   # Time before auto-escalation
TICKET_AUTO_CLOSE_HOURS=2              # Time before auto-close
```

**Adjusting Thresholds:**

- **High-security areas**: Reduce escalation timeout to 5 minutes
- **Low-priority areas**: Increase auto-close to 4 hours
- **24/7 monitoring**: Keep defaults (15 min escalation, 2 hour close)

### Troubleshooting

**Tickets not escalating:**

- Check Celery Beat is running: `celery -A src.celery_app beat`
- Check escalation task in beat schedule: `check-ticket-escalations`
- Verify TICKET_ESCALATION_TIMEOUT_MINUTES in config
- Check ticket status (only OPEN tickets escalate)
- Check acknowledged_at is NULL (acknowledged tickets don't escalate)
- Check Celery logs for errors

**Tickets not auto-closing:**

- Check Celery Beat is running
- Check auto-close task in beat schedule: `auto-close-tickets`
- Verify TICKET_AUTO_CLOSE_HOURS in config
- Check auto_close_at is set on ticket
- Check Celery logs for errors

**Cannot acknowledge ticket:**

- Check ticket status (must be OPEN)
- Verify user is authenticated
- Check ticket is not already acknowledged
- Check ticket is not closed

**Cannot close ticket:**

- Check ticket status (cannot close if already closed)
- Verify user is authenticated
- Check user has permission (assigned user or admin)

**Invalid state transition:**

- Review state machine diagram
- Check current ticket status
- Verify requested transition is valid
- Cannot transition backward (e.g., CLOSED → OPEN)

**Staff cannot see ticket:**

- Staff can only view assigned tickets
- Check ticket.assigned_to == user.id
- Admins can view all tickets
- Assign ticket to user first: `PATCH /api/tickets/{id}/assign`

### Integration with Other Modules

**Creates Tickets:**

- AI Orchestrator (Phase 12) - calls `create_ticket()` when analysis is suspicious

**Uses Tickets:**

- Messenger Service (Phase 10) - sends alerts when tickets created/escalated
- Report Service (Phase 11) - generates reports from ticket data
- Frontend Tickets Page (Phase 15) - displays and manages tickets

**Ticket Data Flow:**

```
AI Analysis (suspicious) → create_ticket() → Link evidence + persons → Send alert
  ↓
User acknowledges → assign to user → Update status
  ↓
Investigate → Update status (IN_PROGRESS → RESOLVED)
  ↓
Close ticket → Generate report → Archive
```

**Auto-Escalation Flow:**

```
Ticket created (status=OPEN)
  ↓
15 minutes pass, no acknowledgment
  ↓
check_ticket_escalations() task runs
  ↓
Set sla_breach=True, escalated=True
  ↓
Send alert to secondary Telegram channel
  ↓
Continue checking every 5 minutes until acknowledged
```

**Auto-Close Flow:**

```
Ticket created (auto_close_at = created_at + 2 hours)
  ↓
2 hours pass
  ↓
auto_close_tickets() task runs
  ↓
Set status=CLOSED, closed_at=now
  ↓
Create TicketHistory entry (event='auto_closed')
```

## Messenger Service (Telegram Integration)

### Overview

VigilentEye integrates with Telegram for real-time security alerts to first responders. The system sends alerts with evidence attachments, ticket details, and interactive acknowledge buttons.

### Features

- **Real-Time Alerts**: Instant notifications to Telegram channels when suspicious activity detected
- **Two-Tier Alerting**: Primary channel for initial alerts, escalation channel for unacknowledged tickets
- **Rich Media**: Send alerts with image/audio evidence attachments
- **Interactive Buttons**: Inline acknowledge button for one-click ticket acknowledgment
- **Retry Mechanism**: Exponential backoff (3 retries: 2s, 4s, 8s delays) for failed sends
- **Rate Limiting**: Max 10 messages/minute to prevent spam and API limits
- **Webhook Callbacks**: Handle button clicks via Telegram webhooks
- **Alert Templates**: Customizable templates for different threat levels

### Obtaining Telegram Credentials

Before setting up the Telegram integration, you need to obtain the necessary credentials. Follow these steps:

**1. Create Bot:**
- Message @BotFather on Telegram
- Use `/newbot` command and follow the prompts
- Choose a name and username for your bot
- Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**2. Create Channel:**
- Create a new Telegram channel or group for alerts
- Add the bot as an administrator with post messages permission
- Ensure the bot has permission to send messages and media

**3. Get Channel ID:**
- Forward a message from your channel to @userinfobot, or
- Use the Telegram API `getUpdates` method to retrieve the channel ID
- Channel IDs are typically negative numbers (format: `-1001234567890` for channels, `-4672336726` for groups)

**4. Generate Webhook Secret:**
- Use `openssl rand -hex 32` to generate a strong random secret
- This secret will be used to verify webhook requests from Telegram

**5. Configure Environment:**
- Copy `.env.example` to `.env`: `cp .env.example .env`
- Fill in the real values in `.env` (never commit `.env` to version control)
- Use placeholders in `.env.example` as a template

**6. Verify Configuration:**
- Test your bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- This should return your bot's information if the token is valid

**Security Note:** Never commit real tokens or secrets to version control. Always use placeholders in `.env.example` and keep real values in `.env` (which is gitignored).

### Telegram Bot Setup

**1. Create Bot with BotFather:**

- Open Telegram and search for @BotFather
- Send `/newbot` command
- Follow prompts to create bot
- Copy bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**2. Create Telegram Channel:**

- Create new Telegram channel for alerts
- Add bot as administrator with post messages permission
- Get channel ID (format: `-1001234567890` for channels, `-4672336726` for groups)
- Use @userinfobot to get channel ID or check bot logs

**3. Configure Environment:**

```env
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_WEBHOOK_SECRET=<your_webhook_secret>
TELEGRAM_PRIMARY_CHANNEL=<your_primary_channel_id>
TELEGRAM_ESCALATION_CHANNEL=<your_channel_id>
```

**4. Set Webhook (Production):**

```bash
# Get admin token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Set webhook
curl -X POST http://localhost:5000/api/telegram/set-webhook \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url":"https://yourdomain.com/api/telegram/webhook"}'
```

### MessengerService

**Core messaging operations:**

```python
from src.services import MessengerService

messenger_service = MessengerService()

# Send alert with image
success, error = messenger_service.send_alert(
    ticket=ticket,
    image_path='storage/evidence/ticket-123/frame_001.jpg'
)

# Send escalation alert
success, error = messenger_service.send_escalation_alert(ticket)

# Handle webhook callback
success, error = messenger_service.handle_callback(
    callback_data='acknowledge:ticket-id',
    user_info={'id': 12345, 'username': 'responder1'}
)
```

### Alert Templates

**Primary Alert (alert.html):**

```
🚨 CRITICAL ALERT

Ticket: #abc12345
Suspicious Activity Detected at 2024-01-15 22:30:42 UTC

Threat Level: CRITICAL
Priority: CRITICAL

Description:
Person holding weapon (knife) in parking lot at night with glass breaking sounds detected.

Evidence: 2 file(s)
Persons: 1 person(s) of interest

⚡ ACTION REQUIRED: Please acknowledge this alert immediately.

---
VigilentEye Security System
```

**Escalation Alert (escalation.html):**

```
🔴🔴🔴 ESCALATION ALERT 🔴🔴🔴
UNACKNOWLEDGED TICKET - IMMEDIATE ATTENTION REQUIRED

⏰ ESCALATION REASON: Ticket not acknowledged within 15 minutes
Escalation Count: 1
Time Since Creation: 18 minutes

[Same ticket details as primary alert]

⚠️ SLA BREACH: Response time exceeded threshold
Expected Response: 15 minutes
Actual Time: 18 minutes

🚨 URGENT ACTION REQUIRED: This ticket requires immediate attention.
First responders did not acknowledge within SLA.

---
⚠️ ESCALATED ALERT - SECONDARY CHANNEL
```

### Retry Mechanism

**Exponential Backoff:**

- **Attempt 1**: Send immediately
- **Attempt 2**: Wait 2 seconds, retry
- **Attempt 3**: Wait 4 seconds, retry
- **Attempt 4**: Wait 8 seconds, retry (final attempt)
- **Total max time**: 14 seconds (2 + 4 + 8)

**Retry Triggers:**

- Network errors (connection timeout, DNS failure)
- Telegram API errors (rate limit, server error)
- Temporary failures (503 Service Unavailable)

**No Retry:**

- Invalid bot token (401 Unauthorized)
- Invalid chat_id (400 Bad Request)
- Permanent errors (bot blocked by user)

### Rate Limiting

**Implementation:**

- Redis key: `telegram:rate_limit:{channel_id}`
- Counter incremented on each send
- Counter expires after 60 seconds (sliding window)
- Max 10 messages per minute per channel

**Behavior:**

- If limit exceeded, return error immediately (no send)
- Log warning with rate limit info
- Wait for counter to expire (max 60 seconds)
- Prevents Telegram API rate limit (30 msg/sec) and spam

**Bypass (Emergency):**

- For critical alerts, consider bypassing rate limit
- Add `bypass_rate_limit=True` parameter to send_alert()
- Document as emergency use only

### Webhook Integration

**Webhook Flow:**

1. User clicks "Acknowledge" button in Telegram
2. Telegram sends POST to `/api/telegram/webhook`
3. Verify webhook secret in header
4. Parse callback_query from payload
5. Extract ticket_id from callback_data
6. Call TicketService.acknowledge_ticket()
7. Answer callback query (show confirmation to user)
8. Edit message to remove button (show acknowledged status)
9. Send confirmation message to channel

**Webhook Payload Example:**

```json
{
  "update_id": 123456789,
  "callback_query": {
    "id": "callback-query-id",
    "from": {
      "id": 12345,
      "username": "responder1",
      "first_name": "John"
    },
    "message": {
      "chat": {"id": -1001234567890},
      "message_id": 456
    },
    "data": "acknowledge:ticket-uuid"
  }
}
```

**Security:**

- Webhook secret verified in `X-Telegram-Bot-Api-Secret-Token` header
- Only Telegram servers know the secret
- Prevents unauthorized callback requests
- Return 403 if verification fails

### Configuration

**Environment Variables:**

```env
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_WEBHOOK_SECRET=<your_webhook_secret>
TELEGRAM_PRIMARY_CHANNEL=<your_primary_channel_id>
TELEGRAM_ESCALATION_CHANNEL=<your_channel_id>
TELEGRAM_RETRY_ATTEMPTS=3
TELEGRAM_RETRY_DELAY=2
TELEGRAM_RATE_LIMIT_MAX=10
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/telegram/webhook
```

### API Endpoints

**POST /api/telegram/webhook**

- Receive webhook callbacks from Telegram
- No authentication (verified by webhook secret)
- Headers: `X-Telegram-Bot-Api-Secret-Token: <secret>`
- Request: Telegram update payload (JSON)
- Response: `{"status": "ok"}` (always 200)

**POST /api/telegram/set-webhook** (Admin Only)

- Configure webhook URL
- Headers: `Authorization: Bearer <admin_token>`
- Request: `{"webhook_url": "https://yourdomain.com/api/telegram/webhook"}`
- Response: `{"message": "Webhook set successfully", "url": "..."}`

**POST /api/telegram/delete-webhook** (Admin Only)

- Remove webhook configuration
- Headers: `Authorization: Bearer <admin_token>`
- Response: `{"message": "Webhook deleted successfully"}`

**GET /api/telegram/webhook-info** (Admin Only)

- Get current webhook configuration
- Headers: `Authorization: Bearer <admin_token>`
- Response: `{"url": "...", "pending_update_count": 0, "last_error_message": null}`

### Troubleshooting

**Alerts not sending:**

- Check bot token is valid: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Verify bot is admin in channel
- Check channel ID is correct (negative for channels/groups)
- Check rate limit not exceeded (max 10/min)
- Check Telegram API status: https://status.telegram.org
- Review logs for Telegram errors

**Webhook not receiving callbacks:**

- Verify webhook URL is HTTPS (Telegram requires HTTPS)
- Check webhook is set: `GET /api/telegram/webhook-info`
- Verify webhook secret matches in header
- Check firewall allows Telegram IPs
- Use ngrok for local testing: `ngrok http 5000`
- Check Telegram webhook logs: `bot.get_webhook_info()`

**Rate limit exceeded:**

- Check Redis connection (rate limiting uses Redis)
- Reduce alert frequency (increase AI confidence threshold)
- Increase rate limit: `TELEGRAM_RATE_LIMIT_MAX=20`
- Check for alert loops (same ticket triggering multiple alerts)

**Retry mechanism not working:**

- Check retry configuration: `TELEGRAM_RETRY_ATTEMPTS=3`, `TELEGRAM_RETRY_DELAY=2`
- Review logs for retry attempts (should see 3 attempts with delays)
- Check if error is retryable (network errors) vs permanent (invalid token)
- Verify exponential backoff delays: 2s, 4s, 8s

**Button not working:**

- Check callback_data format: `acknowledge:{ticket_id}`
- Verify webhook is set and receiving callbacks
- Check ticket status (must be OPEN to acknowledge)
- Review webhook logs for callback_query events
- Verify bot has permission to edit messages

**Images/audio not attaching:**

- Check file paths are correct and files exist
- Verify file size limits (Telegram: 10MB for photos, 50MB for audio)
- Check file format (JPEG/PNG for images, WAV/MP3 for audio)
- Ensure bot has permission to send media in channel

### Integration with Other Modules

**Called by:**

- TicketService.escalate_ticket() - sends escalation alerts (line 292)
- AI Orchestrator (Phase 12) - sends initial alerts when suspicious activity detected
- Celery escalation task - sends auto-escalation alerts for SLA breaches

**Calls:**

- TicketService.acknowledge_ticket() - when acknowledge button clicked
- StorageService.get_file_path() - to get evidence file paths for attachments

**Alert Flow:**

```
Suspicious Activity Detected
  ↓
Create Ticket
  ↓
Send Alert to Primary Channel (with image, acknowledge button)
  ↓
If not acknowledged in 15 minutes:
  ↓
Send Escalation Alert to Secondary Channel
  ↓
User clicks Acknowledge button
  ↓
Webhook callback received
  ↓
Ticket acknowledged, button removed, confirmation sent
```

## Report Generation Service

### Overview

Comprehensive security incident reports in PDF or JSON format with 7 sections, similar person matching, and Redis caching.

### Features

- PDF/JSON export formats
- 7 report sections (executive summary, incident overview, timeline, AI analysis, evidence gallery, persons of interest, environmental context, recommendations)
- Similar person matching from ChromaDB (2-hour time window)
- Redis caching (1-hour TTL) for fast retrieval
- Watermarking for authenticity
- Access control (staff: assigned tickets, admin: all tickets)

### Report Sections

1. Executive Summary - Threat level, statistics, LLM reasoning summary, key factors
2. Incident Overview - Ticket details, timestamps, SLA metrics
3. Timeline - Chronological history of events
4. AI Analysis Results - All 6 AI module outputs
5. Evidence Gallery - Images and audio with captions
6. Persons of Interest - Demographics, similar persons from ChromaDB
7. Environmental Context - Scene analysis, location details
8. Recommendations - LLM recommended actions, next steps

### API Endpoint

**GET /api/tickets/{ticket_id}/report/download?format=pdf|json**

- Download security incident report
- Authorization: Staff (assigned tickets), Admin (all tickets)
- Formats: PDF (default), JSON
- Caching: 1-hour TTL, invalidated on ticket updates

### Configuration

```env
REPORT_CACHE_TTL_SECONDS=3600
REPORT_INCLUDE_SIMILAR_PERSONS=true
REPORT_SIMILAR_PERSONS_TIME_WINDOW=2
REPORT_PAGE_SIZE=letter
```

### Performance

- First generation: ~3-6 seconds (PDF), ~1-2 seconds (JSON)
- Cached retrieval: ~10-20ms (200x faster)
- Similar person search: ~100ms per person

### Troubleshooting

- Report generation fails: Check ReportLab, Jinja2 templates, ticket data
- Similar persons missing: Check ChromaDB, embeddings, time window
- Cache not working: Check Redis connection
- Authorization errors: Check ticket assignment

## AI Orchestrator & Analysis Pipeline

### Overview

The AI Orchestrator coordinates the complete video analysis pipeline, integrating all 6 AI modules (Person Detection, Scene Analysis, Object Detection, Speech-to-Text, Audio Classification, LLM Threat Analysis) with the ticket management and alerting systems.

### Features

- **Automated Pipeline**: Video segmentation → Parallel AI processing → LLM aggregation → Result handling
- **Parallel Execution**: 5 AI modules run simultaneously using Celery groups (30s total vs 150s sequential)
- **Graceful Degradation**: Continue analysis even if some AI modules fail (partial results to LLM)
- **Performance Tracking**: Record inference time for each AI model in database
- **Real-Time Updates**: WebSocket events for UI progress notifications
- **Error Recovery**: Automatic retry with exponential backoff for transient failures
- **Manual Trigger**: API endpoint to analyze videos on-demand
- **Auto-Trigger**: Optional auto-analysis on video upload (disabled by default)

### Analysis Pipeline

**Complete Flow (4 Celery Tasks):**

1. **analyze_video_task** (Entry Point)
   - Updates video status to 'analyzing'
   - Emits WebSocket event: analysis_started
   - Chains to extract_frames_task

2. **extract_frames_task** (Video Segmentation)
   - Extracts frames at 1-second intervals with motion detection
   - Extracts audio track using FFmpeg
   - Saves to temporary directories
   - Tracks performance metrics
   - Emits WebSocket event: frames_extracted
   - Returns: {video_id, frames, audio_path}

3. **run_ai_models_task** (Parallel AI Processing)
   - Selects representative frame (middle frame or highest motion)
   - Runs 5 AI modules in parallel:
     - PersonDetectorService.detect_persons()
     - SceneAnalyzerService.analyze_scene()
     - ObjectDetectorService.detect_objects()
     - SpeechToTextService.transcribe_audio()
     - AudioClassifierService.classify_audio()
   - Aggregates all AI outputs into single dict
   - Runs LLMAnalyzerService.analyze_situation()
   - Tracks performance for each module
   - Emits WebSocket events: ai_processing_started, llm_analysis_complete
   - Returns: {video_id, llm_result, ai_results, frames, audio_path}

4. **handle_suspicious_result_task** (Decision & Actions)
   - Checks if suspicious AND confidence ≥ 0.7
   - If suspicious:
     - Creates ticket via TicketService
     - Stores evidence (frame + audio) via StorageService
     - Links persons to ticket
     - Sends Telegram alert via MessengerService
   - If clean: No action, just update status
   - Updates video.analysis_result ('suspicious' or 'clean')
   - Cleans up temporary files
   - Emits WebSocket event: analysis_complete
   - Returns: {video_id, is_suspicious, ticket_id}

**Total Pipeline Time:**

- Frame extraction: ~5-10s (30s video)
- Parallel AI (5 modules): ~30s (dominated by Whisper)
- LLM analysis: ~500ms
- Result handling: ~2-3s (ticket creation, evidence storage, alert)
- **Total**: ~35-45s for 30s video

### AIOrchestrator Service

**Core orchestration methods:**

```python
from src.services import AIOrchestrator

orchestrator = AIOrchestrator()

# Analyze video (called by Celery task)
result, error = orchestrator.analyze_video(video_id)

# Returns:
# {
#   'is_suspicious': True,
#   'confidence': 0.92,
#   'threat_level': 'high',
#   'reasoning': '...',
#   'recommended_action': 'alert',
#   'key_factors': [...]
# }
```

### API Endpoints

**POST /api/videos/{video_id}/analyze**

- Trigger video analysis manually
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"message": "Video analysis started", "video_id": "uuid", "task_id": "celery-task-id", "status": "analyzing"}`
- Authorization: Users can analyze their own videos, admins can analyze any video
- Returns 202 Accepted (analysis runs asynchronously)

**GET /api/videos/{video_id}/analysis-status**

- Get current analysis status and results
- Headers: `Authorization: Bearer <access_token>`
- Response: `{"video_id": "uuid", "status": "analyzed", "analysis_result": "suspicious", "ticket_id": "uuid", "analyzed_at": "2024-01-15T22:35:00Z"}`
- Status values: 'ready', 'analyzing', 'analyzed', 'error'

### WebSocket Events

**Real-time updates on `/analysis` namespace:**

**Event: `analysis_started`**
- Payload: `{video_id, timestamp}`
- Emitted when: Analysis task starts

**Event: `frames_extracted`**
- Payload: `{video_id, frame_count, timestamp}`
- Emitted when: Frame extraction completes

**Event: `ai_processing_started`**
- Payload: `{video_id, timestamp}`
- Emitted when: AI modules start processing

**Event: `llm_analysis_complete`**
- Payload: `{video_id, is_suspicious, timestamp}`
- Emitted when: LLM analysis completes

**Event: `analysis_complete`**
- Payload: `{video_id, result: 'suspicious'|'clean', ticket_id, threat_level, timestamp}`
- Emitted when: Complete analysis finishes
- **Triggers UI popup notification**

**Event: `analysis_error`**
- Payload: `{video_id, error, timestamp}`
- Emitted when: Analysis fails

**Event: `analysis_progress`**
- Payload: `{video_id, stage, progress: 0-100, timestamp}`
- Emitted during: Long-running operations
- Stages: 'extracting_frames', 'running_ai', 'llm_analyzing', 'handling_result'

**Frontend Integration (Phase 14):**

```javascript
import io from 'socket.io-client'

const socket = io('http://localhost:5000/analysis')

socket.on('analysis_complete', (data) => {
  if (data.result === 'suspicious') {
    toast.error(`Suspicious activity detected! Ticket #${data.ticket_id}`)
  } else {
    toast.success('No suspicious activity detected')
  }
})
```

### Performance Monitoring

**AIPerformanceMetrics Table:**

- Tracks inference time for each AI model
- Fields: task_name, model_name, duration_ms, status, error_message, created_at
- Used by health/metrics endpoint (Phase 13) and analytics dashboard (Phase 15)

**Metrics Tracked:**

- person_detection (yolov8n): ~150ms
- scene_analysis (blip2-opt-2.7b): ~500ms
- object_detection (yolov8n): ~50ms
- speech_to_text (whisper-base): ~30s
- audio_classification (yamnet): ~300ms
- llm_analysis (llama3.2:1b): ~500ms

**Query Metrics:**

```python
# Get average inference time for a task
avg_duration = AIPerformanceMetrics.get_average_duration('person_detection')

# Get recent metrics
recent_metrics = AIPerformanceMetrics.query.filter(
    AIPerformanceMetrics.created_at >= datetime.utcnow() - timedelta(hours=24)
).all()
```

### Error Handling & Graceful Degradation

**Partial AI Failures:**

- If person detection fails: Continue with scene, object, audio analysis
- If scene analysis fails: Use fallback (brightness-based classification)
- If object detection fails: Continue with empty objects list
- If speech-to-text fails: Continue with empty transcription
- If audio classification fails: Continue with empty audio events
- LLM receives partial results and adapts reasoning accordingly

**Complete AI Failure:**

- If all 5 AI modules fail: LLM uses rule-based fallback
- Fallback logic: Check for high-threat indicators in available data
- Lower confidence score (0.6) to indicate fallback used

**LLM Failure:**

- If LLM unavailable: Use rule-based threat assessment
- Rules: High-threat objects OR critical audio events = suspicious
- Confidence: 0.6 (lower than LLM)

**Celery Task Failures:**

- Automatic retry with exponential backoff (max 3 retries)
- If all retries fail: Update video status to 'error'
- Log detailed error information
- Emit error event to UI

### Configuration

**Environment Variables:**

```env
# AI Orchestrator
AI_ORCHESTRATOR_ENABLED=true
AI_ORCHESTRATOR_AUTO_ANALYZE=false
AI_ORCHESTRATOR_PARALLEL_WORKERS=5
AI_ORCHESTRATOR_TIMEOUT_SECONDS=300
AI_ORCHESTRATOR_SAVE_TEMP_FILES=false
AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES=false

# WebSocket
WEBSOCKET_ENABLED=true
WEBSOCKET_ASYNC_MODE=threading
WEBSOCKET_PING_INTERVAL=25
WEBSOCKET_PING_TIMEOUT=60
```

### Troubleshooting

**Analysis not starting:**

- Check video status is 'ready'
- Verify Celery worker is running: `celery -A src.celery_app worker`
- Check Celery logs for task errors
- Verify AI_ORCHESTRATOR_ENABLED=true

**Analysis stuck in 'analyzing' status:**

- Check Celery worker logs for errors
- Check task timeout (default 5 minutes)
- Verify all AI models loaded correctly
- Check for deadlocks in Celery worker

**WebSocket events not received:**

- Check WEBSOCKET_ENABLED=true
- Verify Flask-SocketIO initialized in app.py
- Check frontend Socket.IO client connection
- Review browser console for WebSocket errors
- Verify CORS configuration allows WebSocket connections

**AI modules failing:**

- Check models downloaded: `ls models_cache/`
- Verify GPU available if USE_GPU_INFERENCE=true
- Check memory (need ~8-10GB for all models)
- Review AI module logs for specific errors
- Test individual modules in isolation

**Performance is slow:**

- Enable GPU: USE_GPU_INFERENCE=true (4-5x speedup)
- Use smaller models: WHISPER_MODEL_SIZE=tiny, BLIP2_MODEL_NAME=blip-base
- Reduce frame extraction interval: FRAME_EXTRACTION_INTERVAL=2.0
- Analyze representative frame only: AI_ORCHESTRATOR_ANALYZE_ALL_FRAMES=false
- Increase Celery workers: `celery -A src.celery_app worker --concurrency=4`

**Temporary files not cleaned up:**

- Check AI_ORCHESTRATOR_SAVE_TEMP_FILES=false
- Verify handle_suspicious_result_task completes
- Manually clean: `rm -rf storage/frames/temp_* storage/audio/temp_*`
- Check disk space (cleanup may fail if disk full)

### Integration Example

**Complete End-to-End Flow:**

```python
# 1. User uploads video
video, _ = storage_service.save_video(file, user_id, camera_id)

# 2. User triggers analysis (or auto-triggered)
from src.tasks import analyze_video_task
task = analyze_video_task.delay(video.id)

# 3. Pipeline executes (4 chained tasks)
# Task 1: analyze_video_task → updates status, emits event
# Task 2: extract_frames_task → extracts frames + audio
# Task 3: run_ai_models_task → runs 5 AI modules + LLM
# Task 4: handle_suspicious_result_task → creates ticket if suspicious

# 4. WebSocket events emitted throughout
# - analysis_started
# - frames_extracted (frame_count: 30)
# - ai_processing_started
# - llm_analysis_complete (is_suspicious: true)
# - analysis_complete (result: 'suspicious', ticket_id: 'uuid')

# 5. If suspicious:
# - Ticket created with threat_level='high'
# - Evidence stored (frame + audio)
# - Telegram alert sent to channel
# - UI shows popup: "Suspicious activity detected! Ticket #TKT-001"

# 6. If clean:
# - Video marked as 'clean'
# - UI shows popup: "No suspicious activity detected"
```

**Performance Metrics Dashboard (Phase 15):**

```python
# Query performance metrics
metrics = AIPerformanceMetrics.query.filter(
    AIPerformanceMetrics.created_at >= datetime.utcnow() - timedelta(days=7)
).all()

# Calculate averages
avg_person_detection = AIPerformanceMetrics.get_average_duration('person_detection')
avg_llm_analysis = AIPerformanceMetrics.get_average_duration('llm_analysis')

# Identify slow models
slow_models = AIPerformanceMetrics.query.filter(
    AIPerformanceMetrics.duration_ms > 1000
).order_by(AIPerformanceMetrics.duration_ms.desc()).limit(10).all()
```

## Health Monitoring & Metrics

### Overview

VigilentEye provides comprehensive health monitoring and performance metrics endpoints for system observability, monitoring, and alerting.

### Endpoints

**GET /health (Liveness Check):**

- Purpose: Verify application is running
- Response: `{"status": "healthy", "timestamp": "2024-01-15T10:30:00Z"}`
- Status Code: 200 OK (always, unless app is completely down)
- Authentication: None required (public endpoint)
- Used by: Docker health checks, Kubernetes liveness probes

**GET /health/ready (Readiness Check):**

- Purpose: Verify all dependencies are available
- Checks: MySQL, Redis, ChromaDB, Celery workers, Storage disk space
- Response: `{"ready": true, "checks": [{"name": "mysql", "status": "pass", "response_time_ms": 5.2}, ...], "timestamp": "..."}`
- Status Code: 200 if ready=true, 503 if ready=false
- Authentication: None required
- Used by: Kubernetes readiness probes, load balancers, deployment health checks

**GET /metrics (Performance Metrics):**

- Purpose: Expose performance metrics for monitoring
- Metrics:
  - API latency percentiles (p50, p95, p99) in milliseconds
  - AI model inference times (average per model) in milliseconds
  - Database connection pool stats (size, checked_out, overflow)
  - Storage usage (total, used, free, percentage)
  - Celery worker stats (worker count, active tasks)
- Response: JSON format (default) or Prometheus format (if Accept: text/plain)
- Status Code: 200 OK
- Authentication: None required
- Used by: Frontend Analytics dashboard (auto-refresh every 30s), Prometheus scraper, monitoring tools

### Health Checks

**MySQL Check:**

- Test: Execute `SELECT 1` query
- Measure: Response time in milliseconds
- Status: pass if query succeeds, fail if connection error or timeout
- Uses: Existing `check_db_connection()` from `db_utils.py`

**Redis Check:**

- Test: Execute `PING` command
- Measure: Response time in milliseconds
- Status: pass if ping succeeds, fail if connection error
- Uses: Redis client from config (same pattern as AuthService)

**ChromaDB Check:**

- Test: Call `get_collection_stats()` to verify collections exist
- Measure: Response time in milliseconds
- Status: pass if collections accessible, fail if connection error
- Uses: Existing `ChromaDBManager.get_collection_stats()` method

**Celery Check:**

- Test: Inspect active workers using `celery.control.inspect().active_workers()`
- Count: Number of active workers
- Status: pass if workers > 0, fail if workers = 0
- Additional: Count active tasks for workload monitoring

**Storage Check:**

- Test: Get disk usage using `shutil.disk_usage(STORAGE_BASE_PATH)`
- Calculate: Percentage used = (used / total) * 100
- Status: pass if percentage < 90%, fail if percentage >= 90%
- Warning threshold: 80% (configurable)

### Latency Tracking

**Middleware Implementation:**

- **Before Request**: Record start time in `g.start_time = time.time()`
- **After Request**: Calculate duration: `duration_ms = (time.time() - g.start_time) * 1000`
- **Store**: Add to LatencyTracker: `latency_tracker.add_latency(request.endpoint, duration_ms)`
- **Thread-Safe**: Uses threading.Lock() for concurrent access
- **Memory-Efficient**: Stores last 1000 requests per endpoint (circular buffer)

**Percentile Calculation:**

- Uses numpy.percentile() for accurate percentile calculation
- p50 (median): 50% of requests faster than this
- p95: 95% of requests faster than this (good for SLA monitoring)
- p99: 99% of requests faster than this (identifies outliers)

**Endpoint Grouping:**

- Tracks latencies per Flask endpoint (e.g., 'videos.upload', 'tickets.list')
- Aggregates all endpoints for overall API latency
- Can query specific endpoint latencies for debugging

### AI Performance Metrics

**Data Source:**

- AIPerformanceMetrics table (created in Phase 12)
- Records created by AI Orchestrator for every AI module execution
- Fields: task_name, model_name, duration_ms, status, created_at

**Aggregation:**

- Query last 24 hours of metrics (configurable via METRICS_HISTORY_HOURS)
- Filter by status='success' (exclude failed inferences)
- Group by task_name: person_detection, scene_analysis, object_detection, speech_to_text, audio_classification, llm_analysis
- Calculate average duration_ms for each task

**Metrics Exposed:**

- person_detection: Average YOLOv8 + MTCNN + ArcFace + OSNet + MiVOLO inference time
- scene_analysis: Average BLIP-2 inference time
- object_detection: Average YOLOv8 inference time
- speech_to_text: Average Whisper inference time
- audio_classification: Average YAMNet inference time
- llm_analysis: Average Llama 3.2/Phi-3 inference time

### Request/Response Logging

**Structured Log Format (JSON):**

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Request completed",
  "context": {
    "method": "POST",
    "path": "/api/videos/upload",
    "status": 201,
    "duration_ms": 1234.5,
    "user_id": "user-uuid",
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

**Middleware Implementation:**

- Use `@app.after_request` decorator (added in app.py)
- Extract request context: method, path, status code, duration, user_id (from JWT), IP address, user agent
- Log using existing logger from logging_config.py
- Filter sensitive data: Don't log passwords, tokens, or request bodies with sensitive data
- Skip noisy endpoints: Don't log /health, /metrics (too frequent)

**Log Levels:**

- INFO: Successful requests (2xx, 3xx)
- WARNING: Client errors (4xx)
- ERROR: Server errors (5xx)
- DEBUG: Detailed request/response data (disabled in production)

### Configuration

**Environment Variables:**

```env
HEALTH_CHECK_CACHE_SECONDS=10
METRICS_HISTORY_HOURS=24
LATENCY_TRACKER_MAX_SAMPLES=1000
STORAGE_WARNING_THRESHOLD=80
```

**CORS Configuration:**

- Already configured in app.py for /api/* routes
- Health endpoints at root level (no CORS needed for monitoring tools)
- If CORS needed, add to CORS_ORIGINS in .env

### Performance Considerations

**Health Check Speed:**

- Target: <100ms for /health/ready (all checks combined)
- MySQL check: ~5ms (simple SELECT 1)
- Redis check: ~2ms (PING command)
- ChromaDB check: ~10ms (get_collection_stats)
- Celery check: ~20ms (inspect workers)
- Storage check: ~5ms (disk_usage)
- Total: ~42ms (well under 100ms target)

**Latency Tracking Overhead:**

- Per-request overhead: <1ms (time.time() calls + deque append)
- Memory usage: ~8KB per endpoint (1000 floats * 8 bytes)
- Thread-safe: Lock contention minimal (append is fast)
- Negligible impact on API performance

**Metrics Endpoint Performance:**

- Database query: ~50ms (query AIPerformanceMetrics for 24h)
- Percentile calculation: ~10ms (numpy.percentile on 1000 samples)
- Total: ~100ms (acceptable for metrics endpoint)
- Caching: Can cache metrics for 10s to reduce load (optional)

### Monitoring Integration

**Docker Health Check:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Kubernetes Probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 5
```

**Prometheus Scraping:**

```yaml
scrape_configs:
  - job_name: 'vigilanteye'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

**Frontend Integration:**

- Analytics.tsx already implemented (Phase 15)
- Calls /health and /metrics every 30 seconds via React Query
- Displays health cards and performance charts
- No frontend changes needed

### Troubleshooting

**Health endpoint returns 503:**

- Check which service is failing in 'checks' array
- Verify service is running (MySQL, Redis, ChromaDB, Celery)
- Check network connectivity between backend and services
- Review backend logs for connection errors

**Metrics show zeros:**

- Check if any API requests have been made (latency tracker needs data)
- Verify AIPerformanceMetrics table has records (AI analysis must run)
- Check database query is returning data
- Try making some API requests and check metrics again

**Latency percentiles seem wrong:**

- Check if enough samples collected (need >10 for accurate percentiles)
- Verify numpy.percentile() is calculating correctly
- Check for outliers (very slow requests skewing p99)
- Review latency_data deque contents

**Celery check fails:**

- Verify Celery worker is running: `celery -A src.celery_app worker`
- Check Celery Beat is running: `celery -A src.celery_app beat`
- Review Celery logs for errors
- Check Redis connection (Celery uses Redis as broker)

**Storage check fails:**

- Check STORAGE_BASE_PATH is correct and accessible
- Verify disk space is available (not full)
- Check permissions on storage directory
- Review threshold configuration (STORAGE_WARNING_THRESHOLD)

## Complete AI Analysis Pipeline Example

### End-to-End Flow

This example shows how all 6 AI modules work together to analyze a suspicious situation:

**Scenario: Potential Break-In Detected**

**Step 1: Video Processing**

```python
# Video uploaded at 10:30 PM
video = storage_service.save_video(file, user_id, camera_id='parking-lot-cam-3')
frames = video_processor.extract_frames(video.get_storage_path(), interval=1.0)
audio_path = video_processor.extract_audio(video.get_storage_path())
```

**Step 2: Parallel AI Processing (Frame 42 at timestamp 10:30:42 PM)**

**Vision AI (runs in parallel):**

```python
# Person Detection
persons, _ = person_detector.detect_persons(frame, video.id, timestamp, 42)
# Result: [{
#   'person_id': 'person_abc123',
#   'age': 25, 'gender': 'male',
#   'clothing': 'Dark jacket, black pants',
#   'confidence': 0.89
# }]

# Scene Analysis
scene, _ = scene_analyzer.analyze_scene(frame)
# Result: {
#   'scene_type': 'outdoor',
#   'lighting': 'dark',
#   'time_of_day': 'night',
#   'description': 'Outdoor parking lot at night with poor lighting',
#   'confidence': 0.85
# }

# Object Detection
objects, _ = object_detector.detect_objects(frame, persons)
# Result: {
#   'objects': [{'class_name': 'knife', 'threat_level': 'high', 'confidence': 0.92}],
#   'relationships': [{'person_id': 'person_abc123', 'object_id': 'obj_xyz', 'relationship': 'holding'}],
#   'threat_summary': {'max_threat_level': 'high', 'high_threat_count': 1}
# }
```

**Audio AI (runs in parallel):**

```python
# Speech-to-Text
transcription, _ = speech_to_text.transcribe_audio(audio_path)
# Result: {
#   'transcription': '',  # No speech detected
#   'language': 'unknown',
#   'threat_keywords': [],
#   'confidence': 0.0
# }

# Audio Classification
audio_events, _ = audio_classifier.classify_audio(audio_path)
# Result: {
#   'detected_sounds': [
#     {'class_name': 'Glass', 'urgency_level': 'high', 'timestamp': 42.5, 'confidence': 0.91}
#   ],
#   'urgency_summary': {'max_urgency': 'high', 'high_count': 1},
#   'confidence': 0.91
# }
```

**Step 3: LLM Aggregation and Analysis**

```python
# Aggregate all AI outputs
ai_outputs = {
    'scene': scene,
    'persons': persons,
    'objects': objects,
    'transcription': transcription,
    'audio_events': audio_events,
}

# LLM analysis
analysis, _ = llm_analyzer.analyze_situation(
    ai_outputs=ai_outputs,
    timestamp=datetime(2024, 1, 15, 22, 30, 42),
    location='Parking Lot Camera 3'
)

# Result: {
#   'is_suspicious': True,
#   'confidence': 0.92,
#   'threat_level': 'high',
#   'reasoning': 'This situation is highly suspicious. A person is detected holding a knife (high-threat weapon) in a parking lot at night with poor lighting. Additionally, glass breaking sounds were detected at timestamp 42.5s, suggesting a potential break-in or vandalism. The combination of weapon possession, suspicious timing (night), and breaking sounds indicates a likely security threat requiring immediate attention.',
#   'recommended_action': 'alert',
#   'key_factors': [
#     'Person holding weapon (knife)',
#     'Glass breaking sound detected',
#     'Night time with poor lighting',
#     'Outdoor parking lot (vulnerable location)'
#   ]
# }
```

**Step 4: Decision and Action**

```python
if analysis['is_suspicious'] and analysis['confidence'] >= 0.7:
    # SUSPICIOUS - Take action
    
    # 1. Create ticket
    ticket = ticket_service.create_ticket(
        video_id=video.id,
        title=f"Suspicious Activity Detected at {timestamp}",
        description=analysis['reasoning'],
        priority='high',
        threat_level=analysis['threat_level']
    )
    
    # 2. Store evidence (frame + audio)
    evidence_frame = storage_service.save_frame(
        frame_data=frame,
        ticket_id=ticket.id,
        video_id=video.id,
        timestamp=timestamp,
        frame_number=42,
        description=analysis['reasoning']
    )
    
    evidence_audio = storage_service.save_audio(
        audio_data=audio_data,
        ticket_id=ticket.id,
        video_id=video.id,
        timestamp=timestamp
    )
    
    # 3. Send Telegram alert
    messenger_service.send_alert(
        ticket_id=ticket.id,
        threat_level=analysis['threat_level'],
        message=analysis['reasoning'],
        image=evidence_frame.filepath,
        key_factors=analysis['key_factors']
    )
    
    # 4. Update video analysis status
    video.mark_analyzed('suspicious')
    
    # 5. Log to UI (WebSocket notification)
    websocket.emit('analysis_complete', {
        'video_id': video.id,
        'result': 'suspicious',
        'ticket_id': ticket.id,
        'threat_level': analysis['threat_level']
    })
    
else:
    # NOT SUSPICIOUS - No action needed
    video.mark_analyzed('clean')
    
    # Log to UI
    websocket.emit('analysis_complete', {
        'video_id': video.id,
        'result': 'clean',
        'confidence': analysis['confidence']
    })
```

**Step 5: Report Generation (if ticket created)**

```python
# Generate comprehensive report
report = report_service.generate_report(
    ticket_id=ticket.id,
    include_sections=[
        'incident_overview',
        'timeline',
        'ai_analysis',  # Includes LLM reasoning
        'evidence_gallery',
        'persons_of_interest',
        'recommendations'
    ]
)

# Report includes:
# - LLM reasoning and key factors
# - All AI module outputs (scene, persons, objects, audio)
# - Evidence images and audio
# - Similar person matches from ChromaDB
# - Recommended actions
```

**Performance Metrics:**
- Total processing time: ~4-5s per frame (CPU), ~1-2s (GPU)
- Breakdown:
  - Video processing (frame extraction): ~100ms
  - Person detection: ~200ms
  - Scene analysis: ~500ms
  - Object detection: ~50ms
  - Speech-to-text: ~30s (for 30s audio)
  - Audio classification: ~300ms
  - LLM analysis: ~500ms
  - **Total**: ~32s (dominated by Whisper transcription)

**Optimization:**
- Run vision AI (person, scene, object) in parallel: ~500ms total
- Run audio AI (speech, audio events) in parallel: ~30s total
- Run both groups in parallel: ~30s total (limited by Whisper)
- LLM runs after all AI completes: +500ms
- **Optimized total**: ~30.5s per video analysis
- **Total AI modules loaded**: ~8.6 GB (PersonDetector + SceneAnalyzer + ObjectDetector + SpeechToText + AudioClassifier)

**Optimization Tips:**
- Use smaller BLIP model: `BLIP2_MODEL_NAME=Salesforce/blip-image-captioning-base` (~1GB, 3x faster)
- Disable scene analysis if not needed: set `USE_SCENE_FALLBACK=true` and skip BLIP-2 loading
- Reduce `MAX_OBJECTS_PER_FRAME` for faster processing
- Use GPU for 4-5x speedup

### Troubleshooting

**BLIP-2 download fails:**
- Check internet connection and disk space (need ~6 GB free)
- Check Hugging Face Hub accessibility
- Try smaller model: `Salesforce/blip-image-captioning-base`
- Use fallback mode: `USE_SCENE_FALLBACK=true`

**Scene analysis returns generic descriptions:**
- BLIP-2 may need better quality frames (resolution, lighting)
- Try increasing `BLIP2_MAX_LENGTH` for more detailed captions
- Check if model loaded correctly (check logs)

**Object detection misses items:**
- Lower `OBJECT_DETECTION_CONFIDENCE` threshold (default 0.5)
- Check if object class is in COCO dataset (80 classes)
- Verify frame quality (resolution, lighting)
- Check if `DETECT_ALL_OBJECTS=true` for non-suspicious items

**No object-person relationships detected:**
- Lower `OBJECT_PERSON_IOU_THRESHOLD` (default 0.1)
- Verify person_detections are provided to `detect_objects()`
- Check if objects and persons actually overlap in frame
- Review IoU calculation logic

**Out of memory errors:**
- BLIP-2 requires ~6-8 GB RAM/VRAM
- Use smaller model: `Salesforce/blip-image-captioning-base`
- Disable GPU inference: `USE_GPU_INFERENCE=false`
- Process frames sequentially (not in batches)

**Whisper download fails:**
- Check internet connection and disk space (need ~200 MB free)
- Check firewall settings (allow access to Whisper CDN)
- Manually download model: `python -c "import whisper; whisper.load_model('base')"`
- Try smaller model: `WHISPER_MODEL_SIZE=tiny`

**YAMNet download fails:**
- Check TensorFlow Hub accessibility
- Check disk space (need ~10 MB free)
- Verify TensorFlow installation: `python -c "import tensorflow_hub as hub; print(hub.__version__)"`

**Transcription is empty:**
- Check if audio file has speech (may be silence or noise only)
- Verify audio format is supported (WAV, MP3, FLAC, etc.)
- Check audio quality (sample rate, bit depth)
- Try disabling noise reduction: `ENABLE_NOISE_REDUCTION=false`

**Transcription is inaccurate:**
- Use larger Whisper model: `WHISPER_MODEL_SIZE=small` or `medium`
- Enable noise reduction: `ENABLE_NOISE_REDUCTION=true`
- Check audio quality (low quality = poor transcription)
- Verify language is supported by Whisper (99 languages)

**No audio events detected:**
- Lower confidence threshold: `AUDIO_CLASSIFICATION_CONFIDENCE=0.3`
- Check if audio has actual sounds (may be silence)
- Verify audio format and sample rate
- Check YAMNet model loaded correctly (check logs)

**Speaker diarization inaccurate:**
- Current implementation is simple energy-based (60-70% accuracy)
- For better accuracy, use pyannote.audio (future enhancement)
- Adjust silence detection threshold in code
- Consider disabling if not critical: `ENABLE_SPEAKER_DIARIZATION=false`

### Integration with Other Modules

**Used by:**
- AI Orchestrator (Phase 12) - calls all 5 AI modules (person, scene, object, speech, audio) for each frame/audio
- LLM Analyzer (Phase 8) - consumes structured JSON outputs from all modules
- Report Service (Phase 11) - includes scene context, detected objects, transcription, and audio events in reports

**Uses:**
- ModelManager - for BLIP-2, YOLOv8, Whisper, and YAMNet downloads
- PersonDetector output - for object-person relationship detection
- VideoProcessorService - `extract_audio()` method provides audio files
- Configuration system - for thresholds and model selection

**Output Integration:**
- All modules return structured JSON (no database storage)
- Outputs aggregated by AI Orchestrator with vision module outputs
- Combined with person, scene, object, transcription, and audio event outputs for LLM analysis
- If flagged as suspicious, stored in Evidence.ai_analysis JSON column

**Example Integration:**
```python
# AI Orchestrator calls all 5 modules in parallel
from src.ai_modules import (
    PersonDetectorService,
    SceneAnalyzerService,
    ObjectDetectorService,
    SpeechToTextService,
    AudioClassifierService,
)

# Process frame
persons, _ = person_detector.detect_persons(frame, video_id, timestamp, frame_num)
scene, _ = scene_analyzer.analyze_scene(frame)
objects, _ = object_detector.detect_objects(frame, persons)

# Process audio
transcription, _ = speech_to_text.transcribe_audio(audio_path)
audio_events, _ = audio_classifier.classify_audio(audio_path)

# Aggregate for LLM
llm_input = {
    'scene': scene,
    'persons': persons,
    'objects': objects,
    'transcription': transcription,
    'audio_events': audio_events,
}
```

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

