# VigilantEye Backend API - Postman Collection

This Postman collection provides a complete set of API endpoints for the VigilantEye Backend.

## 📥 Importing the Collection

### Option 1: Import in Postman
1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `VigilantEye-Backend-API.postman_collection.json`
5. Click **Import**

### Option 2: Import via URL
1. Open Postman
2. Click **Import** → **Link**
3. Paste the file path or URL
4. Click **Continue** → **Import**

## 🔧 Configuration

### Collection Variables

The collection uses the following variables (automatically set):

- **`baseUrl`**: `http://localhost:8000/api` - API base URL
- **`accessToken`**: Automatically set after login/signup/refresh
- **`refreshToken`**: Automatically set after login/signup/refresh

### Updating Base URL

To change the base URL:
1. Right-click collection → **Edit**
2. Go to **Variables** tab
3. Update `baseUrl` value
4. Click **Save**

## 🚀 Quick Start

### Step 1: Start Backend Server
```bash
cd backend
start.bat  # Windows
# or
python run.py
```

### Step 2: Authentication Flow

1. **Sign Up** (or use existing account)
   - Open `Authentication` → `Sign Up`
   - Fill in the request body
   - Click **Send**
   - Tokens are automatically saved to collection variables

2. **Login** (alternative)
   - Open `Authentication` → `Login`
   - Fill in email and password
   - Click **Send**
   - Tokens are automatically saved

3. **Use Authenticated Endpoints**
   - All protected endpoints use `{{accessToken}}` automatically
   - No need to manually copy tokens

## 📋 Collection Structure

### 1. Authentication
- **Sign Up** - Register new user
- **Login** - Authenticate and get tokens
- **Refresh Token** - Get new access token
- **Get Current User** - Get user info
- **Verify Token** - Check token validity

### 2. Health Check
- **Health Check** - Basic health status
- **Database Health** - DB connectivity check
- **Performance Metrics** - System metrics
- **System Info** - Detailed system information

### 3. Video Management
- **Upload Video** - Upload video file (multipart/form-data)
- **List Videos** - Get paginated video list
- **Get Video** - Get video details
- **Download Video** - Download video file
- **Delete Video** - Delete video
- **Start Camera Stream** - Start RTSP stream recording

### 4. Video Processing
- **Process Video** - Start video processing (extract frames/audio)
- **Get Processing Status** - Check processing status

### 5. Ticket Management
- **List Tickets** - Get paginated tickets with filters
- **Get Ticket** - Get ticket details
- **Create Ticket** - Create new ticket
- **Update Ticket** - Update ticket information
- **Acknowledge Ticket** - Acknowledge a ticket
- **Close Ticket** - Close a ticket
- **Add Note** - Add note to ticket
- **Get Evidence** - Get ticket evidence
- **Get Statistics** - Get ticket stats (Admin)
- **Delete Ticket** - Delete ticket (Admin)

### 6. Storage Management
- **Get Storage Stats** - Get user storage statistics
- **Get All Storage Stats** - Get all storage stats (Admin)
- **Trigger Cleanup** - Manual cleanup trigger (Admin)

### 7. Model Cache (Admin Only)
- **Get Cache Stats** - Model cache statistics
- **Validate Cache** - Validate cache integrity
- **Clear All Cache** - Clear all cached models
- **Clear Model Cache** - Clear specific model cache
- **Preload Models** - Preload all AI models

### 8. Cleanup (Admin Only)
- **Get Cleanup Status** - Get cleanup service status
- **Get Cleanup Stats** - Get cleanup statistics
- **Trigger Cleanup** - Manually trigger cleanup

## 🔐 Authentication

### Token Management

The collection automatically manages tokens:
- Tokens are saved after **Sign Up**, **Login**, and **Refresh Token**
- All authenticated requests use `{{accessToken}}` automatically
- Tokens expire after 30 minutes (configurable)

### Manual Token Update

If tokens expire:
1. Use **Refresh Token** endpoint
2. Or use **Login** endpoint again
3. Tokens will be automatically updated

## 📝 Request Examples

### Upload Video
- **Method**: POST
- **URL**: `{{baseUrl}}/video/upload`
- **Headers**: `Authorization: Bearer {{accessToken}}`
- **Body**: `multipart/form-data` with `file` field

### Create Ticket
- **Method**: POST
- **URL**: `{{baseUrl}}/tickets`
- **Headers**: 
  - `Authorization: Bearer {{accessToken}}`
  - `Content-Type: application/json`
- **Body**:
```json
{
  "title": "Security Incident",
  "description": "Suspicious activity detected",
  "priority": "HIGH",
  "category": "SECURITY",
  "video_id": 1
}
```

## 🧪 Testing

### Test Scripts

Some endpoints include automatic test scripts:
- **Sign Up/Login/Refresh**: Automatically save tokens
- **Get Current User**: Validates response structure

### Adding Custom Tests

To add tests to any request:
1. Open request → **Tests** tab
2. Add test scripts:
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has data", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('data');
});
```

## 📊 Environment Variables

### Creating Environments

1. Click **Environments** (left sidebar)
2. Click **+** to create new
3. Add variables:
   - `baseUrl`: `http://localhost:8000/api` (dev)
   - `baseUrl`: `https://api.production.com/api` (prod)
4. Select environment before sending requests

## 🔍 Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Token expired → Use Refresh Token endpoint
   - Invalid token → Login again

2. **403 Forbidden**
   - Missing Authorization header
   - Token not set in collection variables

3. **404 Not Found**
   - Check `baseUrl` variable
   - Verify backend server is running

4. **500 Internal Server Error**
   - Check backend logs
   - Verify database connection

### Debug Mode

Enable debug logging:
```bash
cd backend
start-debug.bat  # Windows
```

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/api/docs (when debug mode enabled)
- **ReDoc**: http://localhost:8000/api/redoc
- **Backend README**: `backend/README.md`
- **Example HTTP Requests**: `backend/examples.http`
- **cURL Commands**: `backend/CURL_COMMANDS.md`
- **cURL Script**: `backend/curl-commands.sh`

## 🔄 Collection Updates

To update the collection:
1. Export latest version from Postman
2. Replace `VigilantEye-Backend-API.postman_collection.json`
3. Commit changes to repository

## 📝 Notes

- All Admin endpoints require ADMIN role
- Video uploads limited to 500MB
- Access tokens expire after 30 minutes
- Refresh tokens expire after 7 days
- Default user role is STAFF (requires manual DB update for ADMIN)

