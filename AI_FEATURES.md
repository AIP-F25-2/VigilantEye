# 🤖 AI Features in VigilantEye

VigilantEye now includes advanced AI-powered analytics features for intelligent video surveillance and monitoring.

## 🎯 Overview

The AI Analytics module provides:
- **Object Detection**: Automatic detection of people, vehicles, and objects
- **Anomaly Detection**: Identification of unusual activities and behaviors
- **Behavior Analysis**: Recognition of activities like walking, running, loitering
- **Crowd Density Analysis**: Real-time crowd monitoring and density measurement
- **Smart Alerts**: AI-powered alert generation with severity classification

## 📋 Available Features

### 1. Object Detection
Detects and classifies objects in video frames using computer vision.

**API Endpoint**: `POST /api/ai/detect-objects`

**Features**:
- Detects people, vehicles, and other objects
- Provides bounding boxes and confidence scores
- Tracks objects across frames
- Classifies objects by type (person, vehicle, small/large objects)

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/ai/detect-objects \
  -F "image=@frame.jpg" \
  -F "camera_id=camera_001" \
  -F "min_confidence=0.3"
```

### 2. Anomaly Detection
Identifies unusual patterns and suspicious activities.

**Detected Anomaly Types**:
- **Unusual Motion**: Sudden changes in activity levels
- **Loitering**: People staying in the same area for extended periods
- **Rapid Movement**: Fast-moving objects or people
- **Crowd Density**: Unusually high concentration of people

**API Endpoint**: `POST /api/ai/analyze-frame`

**Example Response**:
```json
{
  "success": true,
  "anomalies": [
    {
      "type": "loitering",
      "confidence": 0.85,
      "location": [320, 240],
      "description": "Loitering detected: object in same area for 45.2s",
      "metadata": {
        "duration_seconds": 45.2,
        "object_type": "person"
      }
    }
  ]
}
```

### 3. Behavior Analysis
Recognizes and classifies human behaviors in video feeds.

**Behavior Types**:
- **Walking**: Normal pedestrian movement
- **Running**: Fast movement
- **Standing**: Stationary position
- **Sitting**: Seated position
- **Loitering**: Lingering in an area
- **Crowd Gathering**: Group formation
- **Vehicle Movement**: Vehicle detection and tracking

**API Endpoint**: `POST /api/ai/analyze-frame`

**Example Response**:
```json
{
  "behaviors": [
    {
      "type": "walking",
      "confidence": 0.75,
      "duration_seconds": 12.5,
      "location": [400, 300],
      "metadata": {
        "avg_speed": 15.2,
        "object_type": "person"
      }
    }
  ]
}
```

### 4. Crowd Density Analysis
Monitors and analyzes crowd density in real-time.

**Density Levels**:
- **Low**: < 10% coverage
- **Medium**: 10-30% coverage
- **High**: 30-50% coverage
- **Very High**: > 50% coverage

**API Endpoint**: `POST /api/ai/analyze-frame`

**Example Response**:
```json
{
  "crowd_density": {
    "density_level": "high",
    "person_count": 15,
    "density_percentage": 35.2,
    "areas": [
      {
        "center": [320, 240],
        "person_count": 5,
        "area": 12500
      }
    ]
  }
}
```

### 5. Smart Alerts
AI-powered alert system with severity classification.

**Alert Severities**:
- **Low**: Minor anomalies or routine events
- **Medium**: Notable events requiring attention
- **High**: Significant events requiring immediate review
- **Critical**: Urgent events requiring immediate action

**API Endpoints**:
- `GET /api/ai/alerts` - Get all alerts
- `POST /api/ai/alerts/<alert_id>/acknowledge` - Acknowledge an alert

## 🔧 API Endpoints

### Status & Health
- `GET /api/ai/status` - Get service status and capabilities

### Object Detection
- `POST /api/ai/detect-objects` - Detect objects in image
- `GET /api/ai/objects` - Get object detection history

### Frame Analysis
- `POST /api/ai/analyze-frame` - Comprehensive AI analysis of a single frame
- `POST /api/ai/analyze-video` - Analyze entire video

### Anomalies
- `GET /api/ai/anomalies` - Get anomaly detection history
  - Query params: `type`, `camera_id`, `unread_only`

### Behaviors
- `GET /api/ai/behaviors` - Get behavior analysis history
  - Query params: `type`, `camera_id`

### Crowd Density
- `GET /api/ai/crowd-density` - Get crowd density analysis history
  - Query params: `camera_id`, `density_level`

### Smart Alerts
- `GET /api/ai/alerts` - Get smart alerts
  - Query params: `type`, `severity`, `unread_only`
- `POST /api/ai/alerts/<alert_id>/acknowledge` - Acknowledge alert

## 🚀 Usage Examples

### Analyze a Single Frame
```python
import requests

url = "http://localhost:8000/api/ai/analyze-frame"
files = {'image': open('frame.jpg', 'rb')}
data = {
    'camera_id': 'camera_001',
    'frame_number': 100
}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"Objects detected: {result['objects_detected']}")
print(f"Anomalies found: {len(result['anomalies'])}")
print(f"Behaviors detected: {len(result['behaviors'])}")
```

### Analyze a Video
```python
import requests

url = "http://localhost:8000/api/ai/analyze-video"
files = {'video': open('surveillance.mp4', 'rb')}
data = {
    'camera_id': 'camera_001',
    'frame_skip': 30  # Process every 30th frame
}

response = requests.post(url, files=files, data=data)
result = response.json()

print(f"Frames processed: {result['frames_processed']}")
print(f"Total anomalies: {result['total_anomalies']}")
print(f"Total behaviors: {result['total_behaviors']}")
```

### Get Recent Anomalies
```python
import requests

url = "http://localhost:8000/api/ai/anomalies"
params = {
    'camera_id': 'camera_001',
    'unread_only': 'true',
    'page': 1,
    'per_page': 20
}

response = requests.get(url, params=params)
anomalies = response.json()

for anomaly in anomalies['anomalies']:
    print(f"{anomaly['anomaly_type']}: {anomaly['description']}")
```

## 🗄️ Database Models

The AI Analytics features use the following database models:

- **ObjectDetection**: Stores object detection results
- **AnomalyDetection**: Stores anomaly detection results
- **BehaviorAnalysis**: Stores behavior analysis results
- **CrowdDensityAnalysis**: Stores crowd density analysis results
- **SmartAlert**: Stores AI-generated alerts

## ⚙️ Configuration

### Environment Variables
No additional environment variables are required. The AI features use existing OpenCV and scikit-learn dependencies.

### Dependencies
The AI features require:
- `opencv-python` (already in requirements.txt)
- `scikit-learn` (already in requirements.txt)
- `numpy` (already in requirements.txt)

## 🔍 How It Works

1. **Object Detection**: Uses OpenCV's background subtraction and contour detection to identify moving objects
2. **Anomaly Detection**: Analyzes motion patterns, object positions, and crowd density to identify anomalies
3. **Behavior Analysis**: Tracks object movement patterns and classifies behaviors based on speed and patterns
4. **Crowd Density**: Calculates person coverage percentage and identifies high-density areas
5. **Smart Alerts**: Automatically generates alerts based on detected anomalies and behaviors

## 📊 Performance Considerations

- **Frame Skipping**: Use `frame_skip` parameter to process every Nth frame for better performance
- **Confidence Thresholds**: Adjust `min_confidence` to filter low-confidence detections
- **Processing Time**: Frame analysis typically takes 50-200ms per frame depending on complexity

## 🎓 Future Enhancements

Potential future AI features:
- Deep learning-based object detection (YOLO, SSD)
- Advanced behavior recognition using neural networks
- Predictive analytics for anomaly forecasting
- Multi-camera tracking and correlation
- Scene understanding and context awareness
- Automated response actions based on alerts

## 📝 Notes

- The AI features work best with clear, well-lit video feeds
- Performance may vary based on video resolution and frame rate
- Some features require minimum object sizes to function effectively
- The system gracefully handles missing dependencies and falls back to basic detection when needed

