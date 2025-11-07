# VigilantEye Backend API - cURL Commands Reference

This document provides cURL command examples for all API endpoints.

## 🔧 Setup

### Variables
```bash
BASE_URL="http://localhost:8000/api"
ACCESS_TOKEN="your_access_token_here"
REFRESH_TOKEN="your_refresh_token_here"
```

### Prerequisites
- `jq` installed for JSON formatting: `brew install jq` (Mac) or `apt-get install jq` (Linux)
- Backend server running on `http://localhost:8000`

## 🔐 Authentication

### Sign Up
```bash
curl -X POST "${BASE_URL}/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'
```

### Login
```bash
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }')

ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')
```

### Refresh Token
```bash
curl -X POST "${BASE_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"${REFRESH_TOKEN}\"
  }"
```

### Get Current User
```bash
curl -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Verify Token
```bash
curl -X GET "${BASE_URL}/auth/verify" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 🏥 Health Check

### Basic Health
```bash
curl -X GET "${BASE_URL}/health"
```

### Database Health
```bash
curl -X GET "${BASE_URL}/health/db"
```

### Performance Metrics
```bash
curl -X GET "${BASE_URL}/health/performance" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### System Info
```bash
curl -X GET "${BASE_URL}/health/system" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 🎥 Video Management

### Upload Video
```bash
curl -X POST "${BASE_URL}/video/upload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "file=@/path/to/video.mp4"
```

### List Videos
```bash
curl -X GET "${BASE_URL}/video?skip=0&limit=50" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Get Video
```bash
VIDEO_ID=1
curl -X GET "${BASE_URL}/video/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Download Video
```bash
VIDEO_ID=1
curl -X GET "${BASE_URL}/video/${VIDEO_ID}/download" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -o "video_${VIDEO_ID}.mp4"
```

### Delete Video
```bash
VIDEO_ID=1
curl -X DELETE "${BASE_URL}/video/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Start Camera Stream
```bash
curl -X POST "${BASE_URL}/video/stream/start" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_url": "rtsp://example.com/stream",
    "duration_seconds": 60
  }'
```

## ⚙️ Video Processing

### Process Video
```bash
VIDEO_ID=1
curl -X POST "${BASE_URL}/video/process/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_ms": 30
  }'
```

### Get Processing Status
```bash
VIDEO_ID=1
curl -X GET "${BASE_URL}/video/process/${VIDEO_ID}/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 🎫 Ticket Management

### List Tickets
```bash
curl -X GET "${BASE_URL}/tickets?status=OPEN&priority=HIGH&skip=0&limit=50" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Get Ticket
```bash
TICKET_ID=1
curl -X GET "${BASE_URL}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Create Ticket
```bash
curl -X POST "${BASE_URL}/tickets" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Security Incident",
    "description": "Suspicious activity detected",
    "priority": "HIGH",
    "category": "SECURITY",
    "video_id": 1
  }'
```

### Update Ticket
```bash
TICKET_ID=1
curl -X PUT "${BASE_URL}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "description": "Updated description",
    "priority": "MEDIUM"
  }'
```

### Acknowledge Ticket
```bash
TICKET_ID=1
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/acknowledge" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Ticket acknowledged and under review"
  }'
```

### Close Ticket
```bash
TICKET_ID=1
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/close" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "resolution": "Issue resolved",
    "note": "Completed successfully"
  }'
```

### Add Note to Ticket
```bash
TICKET_ID=1
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/notes" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Additional information"
  }'
```

### Get Ticket Evidence
```bash
TICKET_ID=1
curl -X GET "${BASE_URL}/tickets/${TICKET_ID}/evidence" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Get Ticket Statistics
```bash
curl -X GET "${BASE_URL}/tickets/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Delete Ticket (Admin)
```bash
TICKET_ID=1
curl -X DELETE "${BASE_URL}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 💾 Storage Management

### Get Storage Stats
```bash
curl -X GET "${BASE_URL}/storage/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Get All Storage Stats (Admin)
```bash
curl -X GET "${BASE_URL}/storage/stats/all" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Trigger Cleanup (Admin)
```bash
curl -X POST "${BASE_URL}/storage/cleanup?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 🤖 Model Cache (Admin Only)

### Get Cache Stats
```bash
curl -X GET "${BASE_URL}/models/cache/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Validate Cache
```bash
curl -X GET "${BASE_URL}/models/cache/validate" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Clear All Cache
```bash
curl -X DELETE "${BASE_URL}/models/cache/clear" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Clear Model Cache
```bash
MODEL_NAME="yolo"
curl -X DELETE "${BASE_URL}/models/cache/clear/${MODEL_NAME}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Preload Models
```bash
curl -X POST "${BASE_URL}/models/cache/preload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 🧹 Cleanup (Admin Only)

### Get Cleanup Status
```bash
curl -X GET "${BASE_URL}/cleanup/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Get Cleanup Stats
```bash
curl -X GET "${BASE_URL}/cleanup/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### Trigger Cleanup
```bash
curl -X POST "${BASE_URL}/cleanup/trigger" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

## 📝 Notes

- Replace `${ACCESS_TOKEN}` and `${REFRESH_TOKEN}` with actual tokens
- Replace `${VIDEO_ID}` and `${TICKET_ID}` with actual IDs
- Add `| jq '.'` to format JSON output (requires `jq` installed)
- Admin endpoints require ADMIN role user
- Video uploads limited to 500MB
- Access tokens expire after 30 minutes

## 🔄 Complete Workflow Example

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api"

# 1. Sign Up
curl -X POST "${BASE_URL}/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'

# 2. Login
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }')

ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')

# 3. Upload Video
curl -X POST "${BASE_URL}/video/upload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "file=@video.mp4"

# 4. Process Video
VIDEO_ID=1
curl -X POST "${BASE_URL}/video/process/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"interval_ms": 30}'

# 5. Create Ticket
curl -X POST "${BASE_URL}/tickets" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Security Incident",
    "description": "Suspicious activity detected",
    "priority": "HIGH",
    "category": "SECURITY",
    "video_id": 1
  }'
```

