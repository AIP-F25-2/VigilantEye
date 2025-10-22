# Storage TTL (Time-To-Live) System Guide

## Overview

The storage system now tracks every file with automatic expiration and cleanup:
- ✅ All files registered in MySQL database
- ✅ Configurable TTL per file type
- ✅ Automatic cleanup every 15 minutes
- ✅ Manual cleanup API
- ✅ TTL extension capabilities
- ✅ Storage statistics

## Database Schema

### storage_files Table

```sql
CREATE TABLE storage_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    video_id INT NULL,
    processing_id VARCHAR(255),
    file_type ENUM('VIDEO', 'FRAME', 'AUDIO', 'THUMBNAIL', 'OTHER'),
    filename VARCHAR(255),
    file_path VARCHAR(500),
    file_size INT,
    mime_type VARCHAR(100),
    metadata TEXT,  -- JSON
    ttl_hours INT DEFAULT 1,
    expires_at DATETIME NOT NULL,
    status ENUM('ACTIVE', 'EXPIRED', 'DELETED', 'PENDING_DELETION'),
    deleted_at DATETIME NULL,
    checksum VARCHAR(64),
    is_processed BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    updated_at DATETIME,
    INDEX(user_id),
    INDEX(video_id),
    INDEX(processing_id),
    INDEX(file_type),
    INDEX(status),
    INDEX(expires_at)
);
```

## Configuration

Add to `.env`:

```env
# Storage TTL (Time To Live in hours)
DEFAULT_FILE_TTL_HOURS=1
VIDEO_TTL_HOURS=24
FRAME_TTL_HOURS=1
AUDIO_TTL_HOURS=1
CLEANUP_INTERVAL_MINUTES=15
```

### TTL Configuration

| File Type | Default TTL | Configurable |
|-----------|-------------|--------------|
| VIDEO | 24 hours | YES |
| FRAME | 1 hour | YES |
| AUDIO | 1 hour | YES |
| THUMBNAIL | 24 hours | YES |
| OTHER | 1 hour | YES |

### Cleanup Schedule

- **Interval**: Every 15 minutes (configurable)
- **Batch Size**: 1000 files per cycle
- **Auto-start**: Yes (starts with application)

## How It Works

### 1. File Registration

When a file is created, it's automatically registered:

```python
await storage_manager.register_file(
    user_id=1,
    file_type=FileType.FRAME,
    file_path="storage/frames/v123_u1_20240115/frame_0001.jpg",
    ttl_hours=1,  # Expires in 1 hour
    video_id=123,
    processing_id="v123_u1_20240115_103045_789"
)
```

### 2. Expiration Calculation

```
created_at = 2024-01-15 10:00:00
ttl_hours = 1
expires_at = 2024-01-15 11:00:00  (created_at + ttl_hours)
```

### 3. Automatic Cleanup

Every 15 minutes:
1. Find files where `expires_at <= NOW()` and `status = ACTIVE`
2. Delete file from disk
3. Update database: `status = DELETED`, `deleted_at = NOW()`

### 4. Lifecycle

```
File Created
    ↓
status = ACTIVE
expires_at = NOW() + ttl_hours
    ↓
[Time passes...]
    ↓
NOW() >= expires_at
    ↓
Cleanup Scheduler finds file
    ↓
Delete from disk
    ↓
status = DELETED
deleted_at = NOW()
    ↓
[Optional: Archive or purge record]
```

## API Endpoints

### Get Storage Statistics

```bash
# User stats
GET /api/storage/stats

# All users stats (Admin only)
GET /api/storage/stats/all
```

**Response:**
```json
{
  "by_type_and_status": {
    "FRAME_ACTIVE": {
      "count": 1000,
      "total_size": 104857600
    },
    "VIDEO_ACTIVE": {
      "count": 5,
      "total_size": 524288000
    }
  },
  "total_files": 1005,
  "total_size_bytes": 629145600,
  "total_size_mb": 600.0,
  "total_size_gb": 0.59
}
```

### Manual Cleanup

```bash
# Trigger cleanup manually (Admin only)
POST /api/storage/cleanup?limit=100
```

**Response:**
```json
{
  "checked": 100,
  "deleted": 95,
  "failed": 5,
  "space_freed": 104857600,
  "space_freed_mb": 100.0
}
```

### Extend File TTL

```bash
# Extend single file
POST /api/storage/file/123/extend?hours=24
```

**Response:**
```json
{
  "file_id": 123,
  "new_expires_at": "2024-01-16T10:00:00",
  "message": "TTL extended by 24 hours"
}
```

### Extend Processing Batch TTL

```bash
# Extend all files in processing batch
POST /api/storage/processing/v123_u1_20240115_103045_789/extend?hours=12
```

**Response:**
```json
{
  "processing_id": "v123_u1_20240115_103045_789",
  "files_updated": 1000,
  "message": "TTL extended by 12 hours for 1000 files"
}
```

### Delete Processing Files

```bash
# Delete all files for a processing batch
DELETE /api/storage/processing/v123_u1_20240115_103045_789
```

**Response:**
```json
{
  "processing_id": "v123_u1_20240115_103045_789",
  "total_files": 1000,
  "deleted": 995,
  "failed": 5,
  "space_freed_mb": 100.5
}
```

## Integration with Video Processing

### Automatic Registration

When video is processed:

```python
# Process video
result = await video_processor.process_video_async(video)

# Frames and audio are automatically registered in storage_files
# with appropriate TTLs:
# - Frames: 1 hour (configurable)
# - Audio: 1 hour (configurable)
```

### Database Records

After processing `v123_u1_20240115_103045_789`:

```sql
SELECT * FROM storage_files WHERE processing_id = 'v123_u1_20240115_103045_789';

-- Results:
-- 1000 frames (FRAME type, ttl=1h)
-- 1 audio file (AUDIO type, ttl=1h)
```

## Usage Examples

### Check User Storage

```python
from src.services.storage_manager import StorageManager

storage_manager = StorageManager(db_session)

stats = await storage_manager.get_storage_stats(user_id=1)
print(f"User has {stats['total_files']} files")
print(f"Total size: {stats['total_size_mb']}MB")
```

### Register New File

```python
storage_file = await storage_manager.register_file(
    user_id=1,
    file_type=FileType.VIDEO,
    file_path="storage/videos/1/video.mp4",
    ttl_hours=24,
    video_id=123,
    mime_type="video/mp4",
    metadata={"duration": 30.5, "resolution": "1920x1080"}
)

print(f"File registered: {storage_file.id}")
print(f"Expires at: {storage_file.expires_at}")
```

### Extend TTL

```python
# Keep important files longer
await storage_manager.extend_file_ttl(file_id=123, hours=48)

# Or extend entire processing batch
await storage_manager.extend_processing_ttl(
    processing_id="v123_u1_20240115_103045_789",
    hours=24
)
```

### Manual Cleanup

```python
result = await storage_manager.cleanup_expired_files(limit=1000)
print(f"Deleted {result['deleted']} files")
print(f"Freed {result['space_freed_mb']}MB")
```

## Monitoring

### Check Expired Files

```sql
-- Find files about to expire
SELECT 
    file_type,
    COUNT(*) as count,
    SUM(file_size) / 1024 / 1024 as total_mb
FROM storage_files
WHERE expires_at <= DATE_ADD(NOW(), INTERVAL 1 HOUR)
    AND status = 'ACTIVE'
GROUP BY file_type;
```

### Storage by User

```sql
-- Storage usage by user
SELECT 
    u.email,
    COUNT(sf.id) as file_count,
    SUM(sf.file_size) / 1024 / 1024 as total_mb
FROM users u
LEFT JOIN storage_files sf ON u.id = sf.user_id
WHERE sf.status = 'ACTIVE'
GROUP BY u.id, u.email
ORDER BY total_mb DESC;
```

### Cleanup History

```sql
-- Recently deleted files
SELECT 
    file_type,
    COUNT(*) as deleted_count,
    SUM(file_size) / 1024 / 1024 as freed_mb,
    DATE(deleted_at) as deletion_date
FROM storage_files
WHERE status = 'DELETED'
    AND deleted_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY file_type, DATE(deleted_at)
ORDER BY deletion_date DESC;
```

## Best Practices

### 1. Set Appropriate TTLs

```env
# Short TTL for processing artifacts
FRAME_TTL_HOURS=1
AUDIO_TTL_HOURS=1

# Longer TTL for source videos
VIDEO_TTL_HOURS=24

# Or even longer for important videos
VIDEO_TTL_HOURS=168  # 1 week
```

### 2. Extend TTL for Important Data

```python
# After successful AI analysis, keep results longer
if analysis_successful:
    await storage_manager.extend_processing_ttl(
        processing_id=processing_id,
        hours=168  # Keep for 1 week
    )
```

### 3. Archive Before Deletion

```python
# Before cleanup, archive important data
async def cleanup_with_archive():
    expired_files = await storage_repo.get_expired_files()
    
    for file in expired_files:
        if file.file_type == FileType.VIDEO:
            # Archive to S3/cloud storage
            await archive_to_cloud(file)
        
        # Then delete
        await storage_manager.cleanup_expired_files()
```

### 4. Monitor Storage Usage

```python
# Daily storage report
stats = await storage_manager.get_storage_stats()
if stats['total_size_gb'] > 100:
    send_alert("Storage usage above 100GB")
```

## Troubleshooting

### Files Not Being Deleted

1. Check scheduler is running:
```python
from src.services.storage_cleanup_scheduler import get_cleanup_scheduler
scheduler = get_cleanup_scheduler()
print(f"Running: {scheduler.is_running}")
```

2. Check for expired files:
```sql
SELECT COUNT(*) FROM storage_files
WHERE expires_at <= NOW() AND status = 'ACTIVE';
```

3. Check logs:
```bash
tail -f logs/app.log | grep "cleanup"
```

### Disk Space Not Freed

1. Verify files actually deleted:
```bash
ls -la storage/frames/v123_u1_20240115_103045_789/
```

2. Check database vs disk:
```sql
SELECT file_path FROM storage_files
WHERE status = 'DELETED'
LIMIT 10;
```

### Performance Issues

1. Index optimization:
```sql
-- Ensure indexes exist
SHOW INDEX FROM storage_files;
```

2. Batch size tuning:
```env
# Reduce if cleanup takes too long
CLEANUP_INTERVAL_MINUTES=30
```

3. Limit cleanup batch:
```python
# In cleanup function, reduce limit
result = await storage_manager.cleanup_expired_files(limit=100)
```

## Migration

To add storage tracking to existing system:

```bash
# 1. Create storage_files table
python scripts/migrate.py reset

# 2. Register existing files (optional)
python scripts/register_existing_files.py

# 3. Restart application
python run.py
```

## Benefits

✅ **Automatic Cleanup** - No manual intervention needed
✅ **Space Management** - Prevents disk space issues  
✅ **Cost Control** - Removes old data automatically
✅ **Compliance** - Data retention policies enforced
✅ **Monitoring** - Track storage usage per user
✅ **Flexibility** - Extend TTL for important files
✅ **Audit Trail** - Track what was deleted and when

## Next Steps

1. ✅ Storage TTL implemented
2. ✅ Automatic cleanup working
3. 🔄 Add cloud archival (S3, Azure, etc.)
4. 🔄 Add storage quotas per user
5. 🔄 Add compression before deletion
6. 🔄 Add restore from archive feature
7. 🔄 Add storage analytics dashboard
