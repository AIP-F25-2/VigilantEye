# VigilantEye API

A REST API backend built with FastAPI and MySQL database.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **MySQL** - Relational database with SQLAlchemy ORM
- **Pydantic** - Data validation and serialization
- **Automatic API Documentation** - Interactive docs at `/docs`
- **CORS Support** - Cross-origin resource sharing enabled
- **Environment Configuration** - Easy configuration management
- **CRUD Operations** - Complete Create, Read, Update, Delete operations
- **Error Handling** - Comprehensive error handling and validation

## Project Structure

```
VigilantEye/
├── main.py              # FastAPI application entry point
├── run.py               # Startup script
├── init_db.py           # Database initialization script
├── config.py            # Configuration settings
├── database.py          # Database connection and session management
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic schemas for request/response validation
├── crud.py              # CRUD operations for database models
├── routers/             # API route modules
│   ├── __init__.py
│   ├── users.py         # User-related endpoints
│   └── items.py         # Item-related endpoints
├── requirements.txt     # Python dependencies
├── env.example          # Environment variables template
└── README.md           # This file
```

## Quick Start

### Option 1: Docker (Recommended)

The easiest way to run the application is using Docker Compose:

#### 1. Clone and Navigate to Project
```bash
cd VigilantEye
```

#### 2. Run with Docker Compose
```bash
# Start all services (MySQL + FastAPI + phpMyAdmin)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### 3. Access the Application
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **phpMyAdmin**: http://localhost:8080 (optional database management)

#### 4. Database Credentials (Docker)
- **Host**: localhost:3306
- **Database**: vigilanteye_db
- **Username**: vigilanteye_user
- **Password**: vigilanteye_password
- **Root Password**: rootpassword

### Option 2: Local Development

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Set Up Environment Variables
Copy the example environment file and configure your database:

```bash
cp env.example .env
```

Edit `.env` with your MySQL database credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=vigilanteye_db
```

#### 3. Create MySQL Database
Create a MySQL database for the application:

```sql
CREATE DATABASE vigilanteye_db;
```

#### 4. Initialize Database Tables
```bash
python init_db.py
```

#### 5. Run the Application
```bash
python run.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /` - Welcome message
- `GET /health` - Health check with database status

### Users
- `POST /api/v1/users/` - Create a new user
- `GET /api/v1/users/` - Get all users (with pagination)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

### Items
- `POST /api/v1/items/` - Create a new item
- `GET /api/v1/items/` - Get all items (with pagination)
- `GET /api/v1/items/{item_id}` - Get item by ID
- `PUT /api/v1/items/{item_id}` - Update item
- `DELETE /api/v1/items/{item_id}` - Delete item

## Example Usage

### Create a User
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "johndoe",
       "email": "john@example.com",
       "full_name": "John Doe"
     }'
```

### Create an Item
```bash
curl -X POST "http://localhost:8000/api/v1/items/" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Sample Item",
       "description": "This is a sample item"
     }'
```

### Get All Users
```bash
curl -X GET "http://localhost:8000/api/v1/users/"
```

## Docker Commands

### Basic Docker Commands
```bash
# Build the application
docker-compose build

# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api
docker-compose logs -f mysql

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: This will delete all data)
docker-compose down -v

# Restart a specific service
docker-compose restart api

# Execute commands in running container
docker-compose exec api bash
docker-compose exec mysql mysql -u vigilanteye_user -p vigilanteye_db
```

### Docker Development
```bash
# Run in development mode with volume mounting
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Rebuild after code changes
docker-compose build --no-cache api
docker-compose up -d api
```

## Development

### Running in Development Mode

The application runs with auto-reload enabled in debug mode. Any changes to the code will automatically restart the server.

### Docker Development Setup
For development with Docker, you can mount your code as a volume to see changes in real-time without rebuilding the container.

### Database Models

The application includes two basic models:

1. **User** - User management
   - id, username, email, full_name, is_active, created_at, updated_at

2. **Item** - Generic item management
   - id, title, description, is_active, created_at, updated_at

### Adding New Models

1. Add the model to `models.py`
2. Create corresponding schemas in `schemas.py`
3. Add CRUD operations in `crud.py`
4. Create router in `routers/`
5. Include router in `main.py`

## Configuration

All configuration is managed through environment variables. See `env.example` for available options.

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in your environment
2. Configure proper CORS origins
3. Use a production ASGI server like Gunicorn with Uvicorn workers
4. Set up proper database connection pooling
5. Configure logging and monitoring

## License

This project is open source and available under the MIT License.