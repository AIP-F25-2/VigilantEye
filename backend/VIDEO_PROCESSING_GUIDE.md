# Video Processing Service Guide

## Overview

The Video Processing Service automatically:
1. **Extracts frames** from videos at configurable intervals
2. **Extracts audio** as separate WAV file
3. **Organizes output** with unique identifiers
4. **Stores metadata** in JSON format

## Directory Structure

```
storage/
├── videos/                    # Original uploaded videos
│   └── {user_id}/
│       └── {uuid}.mp4
│
├── frames/                    # Extracted frames
│   └── {processing_id}/
│       ├── frame_0000_000000ms.jpg
│       ├── frame_0001_000030ms.jpg
│       ├── frame_0002_000060ms.jpg
│       ├── ...
│       └── frames_metadata.json
│
├── audio/                     # Extracted audio
│   └── {processing_id}/
│       ├── audio_{processing_id}.wav
│       └── audio_metadata.json
│
└── processing/                # Complete processing metadata
    └── {processing_id}/
        └── processing_metadata.json
```

## Processing ID Format

Format: `v{video_id}_u{user_id}_{timestamp}`

Example: `v123_u456_20240115_103045_789`

Components:
- `v123` - Video ID
- `u456` - User ID  
- `20240115_103045_789` - Timestamp (YYYYMMDD_HHMMSS_milliseconds)

This ensures:
- ✅ Unique identification
- ✅ Easy tracking per video and user
- ✅ Chronological sorting
- ✅ No collisions

## Frame Extraction

### Configuration

Set in `.env` file:
```env
FRAME_EXTRACTION_INTERVAL_MS=30
```

Default: 30ms (extract 1 frame every 30 milliseconds)

### Frame Naming Convention

Format: `frame_{sequence}_{timestamp}ms.jpg`

Examples:
- `frame_0000_000000ms.jpg` - First frame (at 0ms)
- `frame_0001_000030ms.jpg` - Second frame (at 30ms)
- `frame_0002_000060ms.jpg` - Third frame (at 60ms)
- `frame_0100_003000ms.jpg` - 101st frame (at 3000ms = 3 seconds)

Components:
- **sequence**: 4-digit frame number (0000-9999+)
- **timestamp**: Time in video when frame was captured (in milliseconds)
- **extension**: .jpg (JPEG format, quality 90%)

### Frames Metadata

File: `frames_metadata.json`

```json
{
  "processing_id": "v123_u456_20240115_103045_789",
  "frames_directory": "storage/frames/v123_u456_20240115_103045_789",
  "total_frames_extracted": 1000,
  "extraction_interval_ms": 30,
  "video_fps": 30.0,
  "video_duration_sec": 30.0,
  "video_resolution": "1920x1080",
  "frames": [
    {
      "filename": "frame_0000_000000ms.jpg",
      "path": "storage/frames/.../frame_0000_000000ms.jpg",
      "timestamp_ms": 0,
      "frame_number": 0,
      "sequence": 0
    },
    {
      "filename": "frame_0001_000030ms.jpg",
      "path": "storage/frames/.../frame_0001_000030ms.jpg",
      "timestamp_ms": 30,
      "frame_number": 1,
      "sequence": 1
    }
    // ... more frames
  ]
}
```

## Audio Extraction

### Audio Naming Convention

Format: `audio_{processing_id}.wav`

Example: `audio_v123_u456_20240115_103045_789.wav`

Format: WAV (PCM 16-bit, uncompressed)

### Audio Metadata

File: `audio_metadata.json`

```json
{
  "processing_id": "v123_u456_20240115_103045_789",
  "has_audio": true,
  "audio_directory": "storage/audio/v123_u456_20240115_103045_789",
  "audio_filename": "audio_v123_u456_20240115_103045_789.wav",
  "audio_path": "storage/audio/.../audio_v123_u456_20240115_103045_789.wav",
  "duration_sec": 30.0,
  "sample_rate": 44100,
  "channels": 2,
  "file_size_bytes": 5292000,
  "format": "wav"
}
```

## API Endpoints

### 1. Process Video

**Endpoint:** `POST /api/video/process/{video_id}`

**Request:**
```json
{
  "interval_ms": 30
}
```

**Response:**
```json
{
  "video_id": 123,
  "status": "processing",
  "processing_id": "v123_u456_20240115_103045_789",
  "message": "Video processing started in background"
}
```

Processing runs in background. Status updated in database.

### 2. Check Processing Status

**Endpoint:** `GET /api/video/process/{video_id}/status`

**Response:**
```json
{
  "video_id": 123,
  "status": "COMPLETED",
  "has_results": true,
  "duration": 30.0,
  "resolution": "1920x1080",
  "fps": 30.0
}
```

Status values:
- `UPLOADED` - Video uploaded, not yet processed
- `PROCESSING` - Processing in progress
- `COMPLETED` - Processing completed successfully
- `FAILED` - Processing failed

## Usage Examples

### From API

```javascript
// Upload video first
const uploadResponse = await videoAPI.uploadVideo(file)
const videoId = uploadResponse.id

// Trigger processing with custom interval
const response = await fetch(`/api/video/process/${videoId}`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    interval_ms: 50  // Extract frame every 50ms
  })
})

// Check status
const statusResponse = await fetch(`/api/video/process/${videoId}/status`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

### Standalone Testing

```bash
# Test processing without database
python scripts/test_video_processing.py path/to/video.mp4 --interval 30

# Will output:
# - Frames to storage/frames/{processing_id}/
# - Audio to storage/audio/{processing_id}/
# - Metadata in JSON files
```

## Configuration Options

### Frame Extraction Interval

Controls how often frames are extracted:

| Interval | Frames/Second | Use Case |
|----------|--------------|----------|
| 10ms | 100 | Very detailed analysis |
| 30ms | 33 | Default, good balance |
| 50ms | 20 | Less detail, faster processing |
| 100ms | 10 | Quick overview |
| 1000ms | 1 | One frame per second |

**Trade-offs:**
- Smaller interval = More frames = More storage = Slower processing
- Larger interval = Fewer frames = Less storage = Faster processing

### Storage Paths

Configure in `.env`:
```env
FRAMES_STORAGE_PATH=storage/frames
AUDIO_STORAGE_PATH=storage/audio
VIDEO_STORAGE_PATH=storage/videos
```

## Processing Workflow

```
1. User uploads video
   └─> Video saved to storage/videos/{user_id}/

2. User triggers processing (or automatic)
   └─> POST /api/video/process/{video_id}

3. Background task starts
   ├─> Generate processing_id
   ├─> Update status to PROCESSING
   │
   ├─> Extract frames:
   │   ├─> Read video with OpenCV
   │   ├─> Extract frame every N milliseconds
   │   ├─> Save as JPEG with proper naming
   │   └─> Generate frames_metadata.json
   │
   ├─> Extract audio:
   │   ├─> Read video with MoviePy
   │   ├─> Extract audio track
   │   ├─> Save as WAV
   │   └─> Generate audio_metadata.json
   │
   ├─> Save processing_metadata.json
   ├─> Update video metadata (duration, fps, resolution)
   └─> Update status to COMPLETED

4. User can access processed data
   ├─> Frames in storage/frames/{processing_id}/
   ├─> Audio in storage/audio/{processing_id}/
   └─> Metadata in JSON files
```

## Database Updates

After processing, video record updated with:
- `status` = COMPLETED
- `duration` = Video duration in seconds
- `width` = Video width in pixels
- `height` = Video height in pixels
- `fps` = Frames per second
- `analysis_results` = Complete processing metadata (JSON)

## Example Output

### For a 30-second, 1920x1080, 30fps video with 30ms interval:

**Frames:**
```
storage/frames/v123_u456_20240115_103045_789/
├── frame_0000_000000ms.jpg    (at 0.000s)
├── frame_0001_000030ms.jpg    (at 0.030s)
├── frame_0002_000060ms.jpg    (at 0.060s)
├── frame_0033_001000ms.jpg    (at 1.000s)
├── ...
├── frame_1000_030000ms.jpg    (at 30.000s)
└── frames_metadata.json
```

Total frames: ~1000 frames
Storage: ~50-100MB (depending on content)

**Audio:**
```
storage/audio/v123_u456_20240115_103045_789/
├── audio_v123_u456_20240115_103045_789.wav
└── audio_metadata.json
```

Audio size: ~5MB (44.1kHz, stereo, 30 seconds)

## Performance Considerations

### Processing Time

Approximate times for 1-minute video:
- Frame extraction: 5-15 seconds
- Audio extraction: 2-5 seconds
- **Total: ~10-20 seconds**

Factors affecting speed:
- Video resolution
- Frame interval
- CPU performance
- Disk I/O speed

### Storage Requirements

Per minute of video (1920x1080, 30fps):
- Original video: ~50-200MB
- Frames (30ms interval): ~100-200MB
- Audio (WAV): ~10MB
- **Total: ~160-410MB**

### Recommendations

1. **For Live Analysis**: Use 100ms or larger interval
2. **For Detailed Analysis**: Use 30ms (default)
3. **For Frame-by-Frame**: Use 10ms or extract all frames
4. **For Storage Efficiency**: Use 100ms+ interval

## Error Handling

Common issues and solutions:

### Video Cannot Be Opened
```
Error: Could not open video file
```
**Solutions:**
- Check file exists
- Verify file format
- Check file permissions
- Try re-uploading

### No Audio Track
```
Warning: Video has no audio track
```
**Solution:** This is normal for some videos. Processing continues.

### Out of Disk Space
```
Error: [Errno 28] No space left on device
```
**Solutions:**
- Free up disk space
- Reduce frame interval
- Use external storage

### Memory Error
```
Error: Cannot allocate memory
```
**Solutions:**
- Increase system RAM
- Process smaller videos
- Reduce frame interval

## Testing

### Unit Test
```bash
# Test with sample video
python scripts/test_video_processing.py test_video.mp4

# Test with custom interval
python scripts/test_video_processing.py test_video.mp4 --interval 50
```

### Integration Test
```bash
# Upload video via API
curl -X POST http://localhost:8000/api/video/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.mp4"

# Trigger processing
curl -X POST http://localhost:8000/api/video/process/1 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"interval_ms": 30}'

# Check status
curl http://localhost:8000/api/video/process/1/status \
  -H "Authorization: Bearer TOKEN"
```

## Next Steps

1. ✅ Frame extraction working
2. ✅ Audio extraction working
3. ✅ Organized storage structure
4. ✅ Metadata generation
5. 🔄 Integrate with AI analysis
6. 🔄 Add thumbnail generation
7. 🔄 Add progress tracking
8. 🔄 Add cleanup/archival features

## Cleanup

To free up space, delete old processed files:

```bash
# Delete frames older than 30 days
find storage/frames -type d -mtime +30 -exec rm -rf {} +

# Delete audio older than 30 days
find storage/audio -type d -mtime +30 -exec rm -rf {} +
```

Or implement automatic cleanup in application.
