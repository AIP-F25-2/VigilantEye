# Backend Service

Python FastAPI backend with JWT authentication and MySQL database.

## Features

- ✅ **User Authentication** - JWT-based with access and refresh tokens
- ✅ **Role-Based Access Control** - ADMIN and STAFF roles
- ✅ **Password Security** - Bcrypt hashing with salt
- ✅ **Clean Architecture** - Layered design with clear separation
- ✅ **MySQL Database** - With async SQLAlchemy ORM
- ✅ **API Documentation** - Auto-generated with Swagger/OpenAPI
- ✅ **Error Handling** - Standardized error responses
- ✅ **Logging** - Structured logging with file and console output

## Project Structure

```
backend/
├── src/
│   ├── api/              # API controllers (routes)
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── health.py     # Health check endpoints
│   │   └── dependencies.py  # FastAPI dependencies
│   ├── services/         # Business logic layer
│   │   └── auth.py       # Authentication service
│   ├── repositories/     # Data access layer
│   │   └── user.py       # User repository
│   ├── models/           # Database models
│   │   └── user.py       # User model
│   ├── dto/              # Data Transfer Objects
│   │   ├── auth.py       # Auth DTOs
│   │   └── base.py       # Base DTOs
│   ├── database/         # Database configuration
│   │   ├── base.py       # Base model
│   │   └── session.py    # Session management
│   ├── middleware/       # Custom middleware
│   │   └── error_handler.py
│   ├── utils/            # Utilities
│   │   ├── security.py   # JWT & password utils
│   │   ├── logger.py     # Logging setup
│   │   └── exceptions.py # Custom exceptions
│   ├── config/           # Configuration
│   │   └── settings.py   # App settings
│   └── main.py           # Application entry point
├── scripts/
│   └── migrate.py        # Database migration script
├── requirements/
│   ├── base.txt          # Production dependencies
│   └── development.txt   # Development dependencies
└── .env.example          # Environment variables template
```

## Setup

### 1. Install Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your MySQL credentials
DB_HOST=localhost
DB_PORT=3306
DB_NAME=enterprise_db
DB_USER=root
DB_PASSWORD=your_password

JWT_SECRET_KEY=your-super-secret-key-change-this
```

### 3. Setup MySQL Database

```bash
# Create database
mysql -u root -p
CREATE DATABASE enterprise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 4. Run Migrations

```bash
# Create tables
python scripts/migrate.py create

# To reset database (drop and recreate)
python scripts/migrate.py reset
```

### 5. Run Application

```bash
# Development mode with auto-reload
python src/main.py

# Or using uvicorn directly
uvicorn src.main:app --reload --port 8000
```

## API Endpoints

### Health Check

```http
GET /api/health
GET /api/health/db
```

### Authentication

#### Sign Up
```http
POST /api/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123",
  "full_name": "John Doe"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Get Current User (Authenticate)
```http
GET /api/auth/me
Authorization: Bearer <access_token>

Response:
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "STAFF",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  "permissions": ["users:read"]
}
```

#### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Verify Token
```http
GET /api/auth/verify
Authorization: Bearer <access_token>

Response:
{
  "valid": true,
  "user_id": 1,
  "email": "user@example.com"
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## User Roles

### STAFF (Default)
- Standard user role assigned on signup
- Limited permissions
- Can access their own data

### ADMIN
- Full administrative access
- Can manage all users
- Access to admin-only endpoints

**Note:** To create an admin user, manually update the role in the database:
```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'admin@example.com';
```

## Authentication Flow

### 1. Sign Up Flow
```
Client -> POST /api/auth/signup
       -> Validate input
       -> Check email/username uniqueness
       -> Hash password with bcrypt
       -> Create user with role=STAFF
       -> Generate JWT tokens
       <- Return tokens
```

### 2. Login Flow
```
Client -> POST /api/auth/login
       -> Validate credentials
       -> Verify password hash
       -> Check user is active
       -> Generate JWT tokens
       <- Return tokens
```

### 3. Authenticated Request Flow
```
Client -> GET /api/auth/me
       -> Extract Bearer token
       -> Validate JWT signature
       -> Decode token payload
       -> Get user from database
       -> Check user is active
       <- Return user data
```

## Security Features

1. **Password Hashing**: Bcrypt with configurable rounds
2. **JWT Tokens**: Signed with secret key, includes expiration
3. **Token Types**: Separate access and refresh tokens
4. **Role-Based Access**: Admin and Staff roles
5. **Input Validation**: Pydantic models for request validation
6. **CORS Protection**: Configurable allowed origins
7. **SQL Injection Prevention**: SQLAlchemy ORM with parameters

## Testing

```bash
# Install test dependencies (included in development.txt)
pip install -r requirements/development.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_auth.py
```

## Common Issues

### Database Connection Error
```
Solution: Check MySQL is running and credentials in .env are correct
mysql -u root -p  # Test connection
```

### Import Error
```
Solution: Make sure you're in the backend directory and venv is activated
cd backend
source venv/bin/activate
```

### JWT Token Error
```
Solution: Ensure JWT_SECRET_KEY is set in .env and is sufficiently complex
```

## Development Tips

1. **Use API Documentation**: Visit /api/docs for interactive testing
2. **Check Logs**: Logs are written to `logs/app.log`
3. **Database Reset**: Use `python scripts/migrate.py reset` to start fresh
4. **Environment**: Always use development.txt dependencies for local dev

## Production Considerations

1. **Change JWT Secret**: Use a strong, unique secret key
2. **Disable Debug**: Set `APP_DEBUG=false`
3. **Use HTTPS**: Always use HTTPS in production
4. **Environment**: Use `requirements/production.txt`
5. **Database**: Use production MySQL credentials
6. **Logging**: Configure appropriate log levels
7. **CORS**: Restrict allowed origins to your frontend domain

## Next Steps

- Add email verification
- Implement password reset
- Add more user management endpoints
- Add role management for admins
- Implement refresh token rotation
- Add rate limiting
- Add audit logging
