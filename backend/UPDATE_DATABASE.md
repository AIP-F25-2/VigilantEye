# Database Update Guide

## Add Video Table to Existing Database

If you already have the `users` table and need to add the `videos` table:

### Option 1: Using Migration Script (Recommended)

```bash
cd backend
python scripts/migrate.py create
```

This will automatically create all tables including the new `videos` table.

### Option 2: Manual SQL

If migration fails, run this SQL manually:

```sql
USE vigilanteye_db;

CREATE TABLE IF NOT EXISTS videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL COMMENT 'Unique filename on disk',
    original_filename VARCHAR(255) NOT NULL COMMENT 'Original uploaded filename',
    file_path VARCHAR(500) NOT NULL COMMENT 'Full path to video file',
    file_size INT DEFAULT 0 COMMENT 'File size in bytes',
    mime_type VARCHAR(100),
    duration FLOAT COMMENT 'Video duration in seconds',
    width INT,
    height INT,
    fps FLOAT COMMENT 'Frames per second',
    codec VARCHAR(50),
    status ENUM('UPLOADING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', 'STREAMING') 
        DEFAULT 'UPLOADED' NOT NULL,
    thumbnail_path VARCHAR(500),
    analysis_results TEXT COMMENT 'JSON string of analysis results',
    is_stream BOOLEAN DEFAULT FALSE COMMENT 'Whether this is a camera stream',
    stream_metadata TEXT COMMENT 'JSON string of stream metadata',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

### Option 3: Reset Everything (Development Only!)

⚠️ **WARNING**: This will delete ALL data!

```bash
python scripts/migrate.py reset
```

## Verify Tables Exist

```sql
USE vigilanteye_db;
SHOW TABLES;
DESCRIBE videos;
```

Expected output:
```
+--------------+
| Tables_in_vigilanteye_db |
+--------------+
| users        |
| videos       |
+--------------+
```

## Create Storage Directory

```bash
# From backend directory
mkdir -p storage/videos

# Or on Windows
mkdir storage\videos
```

The application will automatically create user subdirectories when needed.

## Test the Setup

```bash
# Start backend
python run.py

# In another terminal, test video upload
curl -X POST http://localhost:8000/api/video/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@test-video.mp4"
```

## Common Issues

### Foreign Key Constraint Fails
```
Error: Cannot add foreign key constraint
```

**Solution**: Make sure `users` table exists first:
```sql
SHOW TABLES LIKE 'users';
```

### Table Already Exists
```
Error: Table 'videos' already exists
```

**Solution**: Drop and recreate:
```sql
DROP TABLE IF EXISTS videos;
-- Then run CREATE TABLE again
```

### Permission Denied on storage/
```
Error: [Errno 13] Permission denied: 'storage/videos'
```

**Solution**: Create directory with proper permissions:
```bash
mkdir -p storage/videos
chmod 755 storage/videos
```

## Migration Files

The migration will be created in:
```
backend/
  └── alembic/
      └── versions/
          └── xxxx_add_videos_table.py
```

(If using Alembic for migrations)

## Backup Before Migration

Always backup your database before migrations:

```bash
mysqldump -u root -p vigilanteye_db > backup_$(date +%Y%m%d).sql
```

Restore if needed:
```bash
mysql -u root -p vigilanteye_db < backup_20240115.sql
```
