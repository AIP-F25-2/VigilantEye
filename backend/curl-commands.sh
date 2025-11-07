#!/bin/bash
# VigilantEye Backend API - cURL Commands Collection
# Usage: Save as .sh file and make executable: chmod +x curl-commands.sh

BASE_URL="http://localhost:8000/api"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}VigilantEye Backend API - cURL Commands${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Variables (will be set from responses)
ACCESS_TOKEN=""
REFRESH_TOKEN=""

###############################################################################
# Authentication
###############################################################################

echo -e "${GREEN}1. Sign Up${NC}"
curl -X POST "${BASE_URL}/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123",
    "full_name": "Test User"
  }' | jq '.'

echo -e "\n${GREEN}2. Login${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')

echo "Access Token: ${ACCESS_TOKEN:0:50}..."
echo "Refresh Token: ${REFRESH_TOKEN:0:50}..."

echo -e "\n${GREEN}3. Get Current User${NC}"
curl -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}4. Verify Token${NC}"
curl -X GET "${BASE_URL}/auth/verify" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}5. Refresh Token${NC}"
REFRESH_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"${REFRESH_TOKEN}\"
  }")

ACCESS_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.access_token')
echo "New Access Token: ${ACCESS_TOKEN:0:50}..."

###############################################################################
# Health Check
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Health Check${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Health Check${NC}"
curl -X GET "${BASE_URL}/health" | jq '.'

echo -e "\n${GREEN}2. Database Health${NC}"
curl -X GET "${BASE_URL}/health/db" | jq '.'

echo -e "\n${GREEN}3. Performance Metrics${NC}"
curl -X GET "${BASE_URL}/health/performance" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}4. System Info${NC}"
curl -X GET "${BASE_URL}/health/system" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

###############################################################################
# Video Management
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Video Management${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Upload Video${NC}"
echo "Note: Replace '/path/to/video.mp4' with actual video file path"
curl -X POST "${BASE_URL}/video/upload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "file=@/path/to/video.mp4" | jq '.'

echo -e "\n${GREEN}2. List Videos${NC}"
curl -X GET "${BASE_URL}/video?skip=0&limit=50" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}3. Get Video${NC}"
VIDEO_ID=1
curl -X GET "${BASE_URL}/video/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}4. Download Video${NC}"
curl -X GET "${BASE_URL}/video/${VIDEO_ID}/download" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -o "downloaded_video_${VIDEO_ID}.mp4"

echo -e "\n${GREEN}5. Start Camera Stream${NC}"
curl -X POST "${BASE_URL}/video/stream/start" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_url": "rtsp://example.com/stream",
    "duration_seconds": 60
  }' | jq '.'

###############################################################################
# Video Processing
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Video Processing${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Process Video${NC}"
VIDEO_ID=1
curl -X POST "${BASE_URL}/video/process/${VIDEO_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_ms": 30
  }' | jq '.'

echo -e "\n${GREEN}2. Get Processing Status${NC}"
curl -X GET "${BASE_URL}/video/process/${VIDEO_ID}/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

###############################################################################
# Ticket Management
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Ticket Management${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. List Tickets${NC}"
curl -X GET "${BASE_URL}/tickets?status=OPEN&priority=HIGH&skip=0&limit=50" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}2. Get Ticket${NC}"
TICKET_ID=1
curl -X GET "${BASE_URL}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}3. Create Ticket${NC}"
curl -X POST "${BASE_URL}/tickets" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Security Incident",
    "description": "Suspicious activity detected",
    "priority": "HIGH",
    "category": "SECURITY",
    "video_id": 1
  }' | jq '.'

echo -e "\n${GREEN}4. Update Ticket${NC}"
TICKET_ID=1
curl -X PUT "${BASE_URL}/tickets/${TICKET_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "description": "Updated description",
    "priority": "MEDIUM"
  }' | jq '.'

echo -e "\n${GREEN}5. Acknowledge Ticket${NC}"
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/acknowledge" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Ticket acknowledged and under review"
  }' | jq '.'

echo -e "\n${GREEN}6. Close Ticket${NC}"
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/close" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "resolution": "Issue resolved",
    "note": "Completed successfully"
  }' | jq '.'

echo -e "\n${GREEN}7. Add Note to Ticket${NC}"
curl -X POST "${BASE_URL}/tickets/${TICKET_ID}/notes" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "Additional information"
  }' | jq '.'

echo -e "\n${GREEN}8. Get Ticket Evidence${NC}"
curl -X GET "${BASE_URL}/tickets/${TICKET_ID}/evidence" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}9. Get Ticket Statistics${NC}"
curl -X GET "${BASE_URL}/tickets/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

###############################################################################
# Storage Management
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Storage Management${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Get Storage Stats${NC}"
curl -X GET "${BASE_URL}/storage/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}2. Get All Storage Stats (Admin)${NC}"
curl -X GET "${BASE_URL}/storage/stats/all" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}3. Trigger Cleanup (Admin)${NC}"
curl -X POST "${BASE_URL}/storage/cleanup?limit=100" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

###############################################################################
# Model Cache (Admin Only)
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Model Cache (Admin Only)${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Get Cache Stats${NC}"
curl -X GET "${BASE_URL}/models/cache/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}2. Validate Cache${NC}"
curl -X GET "${BASE_URL}/models/cache/validate" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}3. Clear All Cache${NC}"
curl -X DELETE "${BASE_URL}/models/cache/clear" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}4. Clear Model Cache${NC}"
MODEL_NAME="yolo"
curl -X DELETE "${BASE_URL}/models/cache/clear/${MODEL_NAME}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}5. Preload Models${NC}"
curl -X POST "${BASE_URL}/models/cache/preload" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

###############################################################################
# Cleanup (Admin Only)
###############################################################################

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Cleanup (Admin Only)${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}1. Get Cleanup Status${NC}"
curl -X GET "${BASE_URL}/cleanup/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}2. Get Cleanup Stats${NC}"
curl -X GET "${BASE_URL}/cleanup/stats" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${GREEN}3. Trigger Cleanup${NC}"
curl -X POST "${BASE_URL}/cleanup/trigger" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.'

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}All commands completed!${NC}"
echo -e "${BLUE}========================================${NC}"

