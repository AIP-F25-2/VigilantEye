# VigilantEYE Video Streaming & Upload Guide

## Overview

The system now supports two methods for video input:
1. **File Upload** - Upload pre-recorded video files
2. **Live Camera Stream** - Record and stream directly from webcam

## Architecture

```
Frontend (React)              Backend (FastAPI)               Storage
─────────────────            ──────────────────             ────────────
                                                            
File Upload:                                                
┌─────────────┐              ┌──────────────┐             ┌────────────┐
│ File Select │─────────────>│ POST /upload │────────────>│ storage/   │
│   Dialog    │  FormData    │              │   Save File │   videos/  │
└─────────────┘              └──────────────┘             │   user_id/ │
                                     │                     └────────────┘
                                     ↓
                             ┌──────────────┐
                             │  Video Model │
                             │   (MySQL)    │
                             └──────────────┘

Live Stream:
┌─────────────┐              ┌──────────────┐             ┌────────────┐
│   Camera    │──────1──────>│ POST /stream │────────────>│  Create    │
│   Access    │  Start       │    /start    │             │  Empty File│
└─────────────┘              └──────────────┘             └────────────┘
       │                             │
       │ MediaRecorder               │ Return video_id
       ↓                             ↓
┌─────────────┐              ┌──────────────┐             ┌────────────┐
│  Recording  │──────2──────>│ POST /stream │────────────>│  Append    │
│   Chunks    │  Every 1s    │  /:id/chunk  │             │  Chunks    │
└─────────────┘              └──────────────┘             └────────────┘
       │                                                            
       ↓                                                            
┌─────────────┐              ┌──────────────┐             ┌────────────┐
│    Stop     │──────3──────>│ POST /stream │────────────>│  Finalize  │
│  Recording  │              │   /:id/stop  │             │    File    │
└─────────────┘              └──────────────┘             └────────────┘
```

## API Endpoints

### 1. Upload Video File

**Endpoint:** `POST /api/video/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Body: Form data with `file` field

**Example:**
```javascript
const formData = new FormData()
formData.append('file', videoFile)

const response = await fetch('/api/video/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
})
```

**Response:**
```json
{
  "id": 1,
  "filename": "uuid-video.mp4",
  "original_filename": "my-video.mp4",
  "file_size": 15728640,
  "duration": null,
  "status": "UPLOADED",
  "message": "Video uploaded successfully"
}
```

**File Storage:**
```
storage/
  └── videos/
      └── {user_id}/
          └── {uuid}.mp4
```

### 2. Start Camera Stream

**Endpoint:** `POST /api/video/stream/start`

**Request:**
```json
{
  "metadata": {
    "device": "webcam",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Response:**
```json
{
  "id": 2,
  "filename": "stream_20240115_103000_uuid.webm",
  "original_filename": "Camera Stream 20240115_103000",
  "file_size": 0,
  "duration": 0,
  "status": "STREAMING",
  "message": "Stream started successfully"
}
```

### 3. Upload Stream Chunk

**Endpoint:** `POST /api/video/stream/{video_id}/chunk`

**Request:**
- Content-Type: `multipart/form-data`
- Body: Form data with `chunk` field (Blob)

**Example:**
```javascript
const formData = new FormData()
formData.append('chunk', blob)

await fetch(`/api/video/stream/${videoId}/chunk`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`
  },
  body: formData
})
```

**Response:**
```json
{
  "message": "Chunk uploaded successfully"
}
```

### 4. Stop Camera Stream

**Endpoint:** `POST /api/video/stream/{video_id}/stop`

**Response:**
```json
{
  "id": 2,
  "filename": "stream_20240115_103000_uuid.webm",
  "original_filename": "Camera Stream 20240115_103000",
  "file_size": 5242880,
  "duration": 30.5,
  "status": "COMPLETED",
  "message": "Stream stopped successfully"
}
```

### 5. List Videos

**Endpoint:** `GET /api/video/list?skip=0&limit=20`

**Response:**
```json
{
  "videos": [
    {
      "id": 1,
      "user_id": 1,
      "filename": "uuid.mp4",
      "original_filename": "my-video.mp4",
      "file_path": "storage/videos/1/uuid.mp4",
      "file_size": 15728640,
      "mime_type": "video/mp4",
      "duration": 45.2,
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "codec": "h264",
      "status": "COMPLETED",
      "is_stream": false,
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### 6. Get Video Details

**Endpoint:** `GET /api/video/{video_id}`

### 7. Delete Video

**Endpoint:** `DELETE /api/video/{video_id}`

### 8. Download Video

**Endpoint:** `GET /api/video/{video_id}/download`

Returns video file for download.

## Database Schema

### Videos Table

```sql
CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT DEFAULT 0,
    mime_type VARCHAR(100),
    duration FLOAT,
    width INT,
    height INT,
    fps FLOAT,
    codec VARCHAR(50),
    status ENUM('UPLOADING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', 'STREAMING') DEFAULT 'UPLOADED',
    thumbnail_path VARCHAR(500),
    analysis_results TEXT,
    is_stream BOOLEAN DEFAULT FALSE,
    stream_metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);
```

## Frontend Implementation

### File Upload

```javascript
// Select file
const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file && file.type.startsWith('video/')) {
    setSelectedFile(file)
  }
}

// Upload file
const handleUpload = async () => {
  const response = await videoAPI.uploadVideo(selectedFile, (progress) => {
    setUploadProgress(progress)
  })
  console.log('Uploaded:', response)
}
```

### Camera Streaming

```javascript
// Start camera
const startCamera = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 1280, height: 720 },
    audio: false,
  })
  videoRef.current.srcObject = stream
  mediaStreamRef.current = stream
}

// Start recording
const startRecording = async () => {
  // Start stream on backend
  const response = await videoAPI.startStream({
    device: 'webcam',
    timestamp: new Date().toISOString(),
  })
  const videoId = response.id

  // Create MediaRecorder
  const mediaRecorder = new MediaRecorder(mediaStreamRef.current, {
    mimeType: 'video/webm;codecs=vp9'
  })

  // Upload chunks
  mediaRecorder.ondataavailable = async (event) => {
    if (event.data && event.data.size > 0) {
      await videoAPI.uploadChunk(videoId, event.data)
    }
  }

  mediaRecorder.start(1000) // Collect data every 1 second
}

// Stop recording
const stopRecording = async () => {
  mediaRecorder.stop()
  await videoAPI.stopStream(videoId)
}
```

## Video Processing Status

| Status | Description |
|--------|-------------|
| UPLOADING | File is being uploaded |
| UPLOADED | File uploaded, awaiting processing |
| PROCESSING | AI analysis in progress |
| COMPLETED | Processing complete |
| FAILED | Processing failed |
| STREAMING | Live camera stream active |

## File Storage Structure

```
backend/
  └── storage/
      └── videos/
          ├── 1/                    # User ID 1
          │   ├── abc123.mp4       # Uploaded video
          │   ├── def456.webm      # Camera stream
          │   └── ghi789.mp4       # Another video
          └── 2/                    # User ID 2
              └── jkl012.mp4
```

## Security Features

1. **Authentication Required** - All endpoints require valid JWT token
2. **User Isolation** - Users can only access their own videos
3. **File Validation** - Only video formats accepted
4. **Size Limits** - Max 500MB per upload
5. **Path Security** - Files stored with UUID names
6. **Ownership Check** - All operations verify user owns the video

## Performance Considerations

1. **Chunked Upload** - Streams upload in 1-second chunks
2. **Async Processing** - File saving doesn't block response
3. **Database Indexing** - User ID indexed for fast queries
4. **File Streaming** - Large files served efficiently

## Testing

### Test File Upload
```bash
curl -X POST http://localhost:8000/api/video/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test-video.mp4"
```

### Test Stream Flow
```bash
# 1. Start stream
curl -X POST http://localhost:8000/api/video/stream/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"device": "test"}}'

# 2. Upload chunk (repeat as needed)
curl -X POST http://localhost:8000/api/video/stream/1/chunk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chunk=@chunk.webm"

# 3. Stop stream
curl -X POST http://localhost:8000/api/video/stream/1/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Upload Fails
- Check file size (max 500MB)
- Verify video format
- Check disk space

### Stream Chunks Not Saving
- Verify video_id exists
- Check stream status is STREAMING
- Ensure chunks are sent as FormData

### Camera Access Denied
- Browser requires HTTPS for camera (except localhost)
- Check browser permissions
- Try different browser

## Next Steps

1. ✅ Basic upload working
2. ✅ Camera streaming working
3. 🔄 Add video metadata extraction (duration, resolution)
4. 🔄 Generate thumbnails
5. 🔄 Integrate AI analysis
6. 🔄 Add progress tracking
7. 🔄 Implement video playback
8. 🔄 Add video list page

## Resources

- MediaRecorder API: https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder
- FastAPI File Upload: https://fastapi.tiangolo.com/tutorial/request-files/
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
