# Quick Start Guide

Get the authentication system running in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- MySQL 5.7+ or MariaDB 10.3+
- pip (Python package manager)

## Step 1: Setup MySQL Database

```bash
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE enterprise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user (optional, for better security)
CREATE USER 'enterprise_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON enterprise_db.* TO 'enterprise_user'@'localhost';
FLUSH PRIVILEGES;

# Exit MySQL
EXIT;
```

## Step 2: Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt
```

## Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# At minimum, update these:
```

Edit `.env`:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=enterprise_db
DB_USER=root  # or enterprise_user if you created one
DB_PASSWORD=your_mysql_password

JWT_SECRET_KEY=change-this-to-a-random-secret-key-at-least-32-characters-long
```

## Step 4: Create Database Tables

```bash
# Run migration script
python scripts/migrate.py create
```

You should see:
```
INFO - Creating database tables...
INFO - Database tables created successfully
```

## Step 5: Start the Server

```bash
# Start the development server
python src/main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO - Starting application...
INFO - Database initialized
INFO - Application started - Environment: development
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 6: Test the API

### Option A: Using Browser

1. Open your browser and go to: `http://localhost:8000/api/docs`
2. You'll see the interactive Swagger UI
3. Try the `/api/health` endpoint first

### Option B: Using curl

```bash
# Test health check
curl http://localhost:8000/api/health

# Sign up a new user
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "TestPass123",
    "full_name": "Test User"
  }'

# You'll get back tokens like:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer",
#   "expires_in": 1800
# }

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }'

# Get current user info (replace YOUR_TOKEN with the access_token from above)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Option C: Using the included HTTP file

If you use VS Code with the REST Client extension:

1. Open `backend/examples.http`
2. Click "Send Request" above any request
3. See the response inline

## Common Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/health` | Health check | No |
| POST | `/api/auth/signup` | Create new user | No |
| POST | `/api/auth/login` | Login user | No |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/refresh` | Refresh token | No |
| GET | `/api/auth/verify` | Verify token | Yes |

## Example: Complete Flow

### 1. Sign Up
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "johndoe",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 2. Get User Info
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer eyJhbGc..."
```

Response:
```json
{
  "user": {
    "id": 1,
    "email": "john@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "STAFF",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "permissions": ["users:read"]
}
```

## Troubleshooting

### "Can't connect to MySQL server"
- Ensure MySQL is running: `mysql -u root -p`
- Check credentials in `.env` file
- Verify database exists: `SHOW DATABASES;`

### "ModuleNotFoundError"
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements/development.txt`
- Check you're in the `backend` directory

### "Table doesn't exist"
- Run migrations: `python scripts/migrate.py create`
- To reset database: `python scripts/migrate.py reset`

### "Invalid token"
- Token might be expired (30 min default)
- Use refresh token to get new access token
- Ensure Bearer token format: `Authorization: Bearer YOUR_TOKEN`

### Port already in use
- Change port in `.env`: `APP_PORT=8001`
- Or kill process using port 8000

## Next Steps

1. **Create an Admin User**: 
   ```sql
   UPDATE users SET role = 'ADMIN' WHERE email = 'john@example.com';
   ```

2. **Explore API Documentation**: 
   Visit `http://localhost:8000/api/docs`

3. **Add More Features**:
   - Create new models in `src/models/`
   - Add repositories in `src/repositories/`
   - Implement services in `src/services/`
   - Create controllers in `src/api/`

4. **Connect Frontend**: 
   Use the tokens for authenticated requests from your React app

5. **Read Full Documentation**: 
   Check `backend/README.md` for detailed information

## Architecture at a Glance

```
Request → Controller (API) → Service (Business Logic) → Repository (Data Access) → Database
                                                                                      ↓
Response ← Controller ← Service ← Repository ←────────────────────────────────────┘
```

## Key Files

- `src/main.py` - Application entry point
- `src/api/auth.py` - Authentication endpoints
- `src/services/auth.py` - Authentication business logic
- `src/repositories/user.py` - User data access
- `src/models/user.py` - User database model
- `src/config/settings.py` - Configuration management

## Support

If you encounter issues:
1. Check the logs in `logs/app.log`
2. Verify all environment variables in `.env`
3. Ensure database is accessible
4. Check Python version: `python --version` (should be 3.10+)

Happy coding! 🚀
