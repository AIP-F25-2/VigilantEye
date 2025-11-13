# 🤖 Face & Identity Agent - VIGILANTEye Multi-Agent Video Intelligence

## 🎯 Overview

The **Face & Identity Agent** is a core component of VIGILANTEye's Multi-Agent Video Intelligence system, designed to provide advanced face detection, recognition, re-identification, and watchlist management for CCTV surveillance systems.

## 🏗️ Architecture

### Core Components

1. **FaceIdentityAgent** - Main agent orchestrating all face-related operations
2. **WatchlistManager** - Manages employee, VIP, and suspect watchlists
3. **DisguiseDetector** - Detects masks, hats, glasses, and other disguises
4. **CrossAgeDetector** - Handles face recognition across different age groups
5. **PersonIdentity** - Data structure representing person identity information

### Key Features

- **Face Detection & Recognition**: Multi-method detection using HOG + CNN models
- **Cross-Camera Re-identification**: Track persons across multiple camera feeds
- **Watchlist Integration**: Employee, VIP, and suspect management
- **Disguise Detection**: Identify masks, hats, glasses, beards
- **Cross-Age Recognition**: Handle face recognition across different age groups
- **Demographics Analysis**: Age and gender estimation (privacy configurable)
- **Real-time Processing**: Live CCTV video analysis
- **Database Persistence**: Store all detection and identity data

## 🚀 API Endpoints

### CCTV Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cctv/status` | Get agent status and tracking summary |
| `POST` | `/api/cctv/process` | Process CCTV video for face detection |
| `GET` | `/api/cctv/tracking` | Get person tracking information |
| `GET` | `/api/cctv/cameras` | Get camera status and activity |

### Watchlist Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cctv/watchlist` | Get watchlist members |
| `POST` | `/api/cctv/watchlist` | Add person to watchlist |
| `DELETE` | `/api/cctv/watchlist/<id>` | Remove person from watchlist |

### Alerts & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cctv/alerts` | Get recent watchlist alerts |

## 🎯 Usage Examples

### 1. Process CCTV Video

```bash
curl -X POST "https://your-app.azurecontainerapps.io/api/cctv/process" \
  -F "video=@cctv_feed.mp4" \
  -F "camera_id=camera_001" \
  -F "frame_skip=30" \
  -F "privacy_mode=false"
```

**Response:**
```json
{
  "success": true,
  "video_path": "uploads/cctv_videos/cctv_feed_1234567890.mp4",
  "camera_id": "camera_001",
  "frames_processed": 150,
  "detections_saved": 45,
  "processing_summary": {
    "total_faces": 89,
    "unique_persons": 12,
    "watchlist_matches": 3
  }
}
```

### 2. Add Person to Watchlist

```bash
curl -X POST "https://your-app.azurecontainerapps.io/api/cctv/watchlist" \
  -F "image=@employee_photo.jpg" \
  -F "person_type=employee" \
  -F "name=John Doe" \
  -F 'metadata={"department": "IT", "access_level": "high"}'
```

**Response:**
```json
{
  "success": true,
  "person_id": "employee_1234567890",
  "person_type": "employee",
  "name": "John Doe",
  "message": "Added John Doe to employee watchlist"
}
```

### 3. Get Person Tracking

```bash
curl "https://your-app.azurecontainerapps.io/api/cctv/tracking"
```

**Response:**
```json
{
  "success": true,
  "tracking_summary": {
    "total_persons": 25,
    "watchlist_persons": 8,
    "cameras_active": 3,
    "recent_activity": [
      {
        "person_id": "person_000001",
        "person_type": "employee",
        "last_seen": "2025-01-15T10:30:00Z",
        "cameras": ["camera_001", "camera_002"]
      }
    ]
  }
}
```

## 🌐 Web Interface

### CCTV Intelligence Dashboard
- **Access**: `https://your-app.azurecontainerapps.io/cctv`
- **Features**:
  - Real-time person tracking
  - Watchlist management
  - Camera status monitoring
  - Alert management
  - Video processing interface

### Dashboard Tabs

1. **Person Tracking**: View all detected persons with confidence scores
2. **Watchlist**: Manage employee, VIP, and suspect lists
3. **Cameras**: Monitor camera activity and status
4. **Alerts**: View recent watchlist matches and alerts

## 🔧 Configuration

### Environment Variables

```bash
# CCTV Processing Configuration
CCTV_VIDEOS_DIR=app/cctv_videos
WATCHLIST_DIR=data/watchlists
FACE_SIMILARITY_THRESHOLD=0.4
PRIVACY_MODE=false
FRAME_SKIP_DEFAULT=30
```

### Watchlist Structure

```
data/watchlists/
├── employees.json      # Employee watchlist
├── vips.json          # VIP watchlist
├── suspects.json      # Suspect watchlist
└── face_encodings.pkl # Face encodings cache
```

### Person Types

- **Employee**: Company staff members
- **VIP**: Important persons requiring special attention
- **Suspect**: Persons of interest or security concern
- **Unknown**: Unidentified persons
- **Visitor**: Temporary visitors

## 🎯 Core Features Implementation

### 1. Face Detection & Recognition

```python
# Multi-method face detection
face_locations = face_recognition.face_locations(image, model="hog")
face_encodings = face_recognition.face_encodings(image, face_locations)

# Cross-camera re-identification
similarity = 1 - face_recognition.face_distance([known_encoding], unknown_encoding)[0]
```

### 2. Watchlist Management

```python
# Add person to watchlist
agent.add_to_watchlist(
    person_type=PersonType.EMPLOYEE,
    name="John Doe",
    face_image=face_image,
    metadata={"department": "IT"}
)

# Check against watchlist
is_on_watchlist, person_type = agent.watchlist_manager.is_on_watchlist(person_id)
```

### 3. Disguise Detection

```python
# Detect disguises
disguises = disguise_detector.detect_disguises(face_image)
# Returns: [DisguiseType.MASK, DisguiseType.HAT, DisguiseType.GLASSES]
```

### 4. Cross-Age Recognition

```python
# Compare faces across age groups
similarity = cross_age_detector.cross_age_compare(
    encoding1, encoding2, age1, age2
)
```

### 5. Demographics Analysis

```python
# Get demographics (privacy configurable)
demographics = agent._get_demographics(face_image, person_identity)
# Returns: {"gender": "Male", "age_group": "(25-32)", "confidence": 0.85}
```

## 📊 Database Schema

### Face Detection Table
```sql
CREATE TABLE face_detections (
    id VARCHAR(36) PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL,
    source_path VARCHAR(500),
    video_id VARCHAR(36),
    frame_number INT,
    faces_detected INT DEFAULT 0,
    detection_results JSON,
    processing_time_ms FLOAT,
    created_at DATETIME DEFAULT NOW()
);
```

### Face Encoding Table
```sql
CREATE TABLE face_encodings (
    id VARCHAR(36) PRIMARY KEY,
    person_id VARCHAR(100) NOT NULL,
    face_detection_id VARCHAR(36),
    face_encoding JSON NOT NULL,
    bounding_box JSON,
    is_known_person BOOLEAN,
    confidence_score FLOAT,
    created_at DATETIME DEFAULT NOW()
);
```

## 🚀 Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Watchlist Directory

```bash
mkdir -p data/watchlists
```

### 3. Run Database Migration

```bash
flask db upgrade
```

### 4. Deploy to Azure

```bash
docker build -t your-registry.azurecr.io/vigilanteye:latest .
docker push your-registry.azurecr.io/vigilanteye:latest
```

## 🔍 Monitoring & Troubleshooting

### Agent Status Check

```bash
curl https://your-app.azurecontainerapps.io/api/cctv/status
```

**Expected Response:**
```json
{
  "success": true,
  "agent_status": "active",
  "tracking_summary": {
    "total_persons": 25,
    "watchlist_persons": 8,
    "cameras_active": 3
  },
  "privacy_mode": false,
  "similarity_threshold": 0.4
}
```

### Common Issues

1. **Face Detection Not Working**
   - Check if FaceAi service is available
   - Verify model files are present
   - Check video file format and quality

2. **Watchlist Issues**
   - Ensure watchlist directory exists
   - Check file permissions
   - Verify face encoding generation

3. **Performance Issues**
   - Adjust frame_skip parameter
   - Enable privacy mode for faster processing
   - Check system resources

## 🎯 Integration with Multi-Agent System

### Agent Communication

The Face & Identity Agent integrates with other VIGILANTEye agents:

- **Anomaly Detection Agent**: Provides person identity context
- **Action Recognition Agent**: Associates actions with specific persons
- **Alert Management Agent**: Triggers alerts for watchlist matches
- **Analytics Agent**: Provides demographics and tracking data

### Data Flow

1. **Video Input** → Face Detection → Person Identification
2. **Watchlist Check** → Alert Generation → Notification
3. **Cross-Camera Tracking** → Person Re-identification
4. **Demographics Analysis** → Analytics Data
5. **Database Storage** → Historical Tracking

## 🔮 Future Enhancements

### Planned Features

- **Real-time Video Streaming**: Live camera feed processing
- **Advanced Disguise Detection**: AI-powered disguise recognition
- **Emotion Recognition**: Facial expression analysis
- **Gait Analysis**: Walking pattern recognition
- **Multi-modal Fusion**: Combine face with other biometrics

### Performance Optimizations

- **GPU Acceleration**: CUDA support for faster processing
- **Model Quantization**: Optimized models for edge deployment
- **Caching**: Redis integration for faster lookups
- **Async Processing**: Background job processing

---

**The Face & Identity Agent is now fully integrated and ready for production use!** 🎉

This agent provides the foundation for VIGILANTEye's Multi-Agent Video Intelligence system, enabling advanced person tracking, recognition, and watchlist management across CCTV surveillance networks.

