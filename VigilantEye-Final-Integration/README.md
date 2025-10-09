# VigilantEye - Video Management API

A comprehensive Flask REST API for video management with MySQL database, Docker support, and phpMyAdmin interface.

## Project Structure

```
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/                  # Database models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model with common fields
│   │   ├── user.py              # User model
│   │   ├── video.py             # Video model
│   │   ├── recording.py         # Recording models
│   │   ├── frame.py             # Frame models
│   │   ├── clip.py              # Clip model
│   │   ├── segment.py           # Segment model
│   │   ├── device.py            # Device models
│   │   ├── project.py           # Project models
│   │   └── analytics.py         # Analytics models
│   ├── controllers/             # API controllers
│   │   ├── __init__.py
│   │   ├── main.py              # Health check endpoints
│   │   ├── api.py               # User API endpoints
│   │   ├── video_controller.py  # Video API endpoints
│   │   ├── recording_controller.py # Recording API endpoints
│   │   └── project_controller.py # Project API endpoints
│   └── schemas/                 # Marshmallow schemas
│       ├── __init__.py
│       ├── user_schema.py       # User validation schemas
│       ├── video_schema.py      # Video validation schemas
│       ├── recording_schema.py  # Recording validation schemas
│       ├── frame_schema.py      # Frame validation schemas
│       ├── clip_schema.py       # Clip validation schemas
│       ├── segment_schema.py    # Segment validation schemas
│       ├── device_schema.py     # Device validation schemas
│       ├── project_schema.py    # Project validation schemas
│       └── analytics_schema.py  # Analytics validation schemas
├── migrations/                   # Database migrations
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml           # Docker Compose setup
├── run.py                       # Application entry point
└── README.md                    # This file
```

## Features

- **Flask REST API** with comprehensive video management
- **SQLAlchemy ORM** for database operations
- **MySQL** database with Docker
- **phpMyAdmin** for database management
- **Flask-Migrate** for database migrations
- **Marshmallow** for data validation and serialization
- **CORS** support for cross-origin requests
- **Docker** and **Docker Compose** setup
- **Base Model** with common fields (id, created_at, updated_at)
- **Multiple Models**: Users, Videos, Recordings, Frames, Clips, Segments, Devices, Projects, Analytics
- **Video Processing**: Upload, metadata extraction, frame analysis
- **Recording Management**: Live recording sessions with device support
- **Project Collaboration**: Multi-user project management
- **Analytics**: View tracking and usage analytics

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd VigilantEye
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the services:**
   - **Flask API**: `http://localhost:5000`
   - **Health Check**: `http://localhost:5000/health`
   - **API Endpoints**: `http://localhost:5000/api/`
   - **phpMyAdmin**: `http://localhost:8080`
     - Username: `root`
     - Password: `rootpass`

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   export DATABASE_URL=mysql+pymysql://flaskuser:flaskpass@localhost:3306/flaskapi
   export SECRET_KEY=your-secret-key-here
   ```

3. **Initialize database:**
   ```bash
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health check

### User Management (v1)
- `GET /api/users` - Get all users
- `GET /api/users/{id}` - Get user by ID
- `POST /api/users` - Create new user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Video Management (v2)
- `GET /api/v2/videos` - Get all videos
- `GET /api/v2/videos/{id}` - Get video by ID
- `POST /api/v2/videos` - Upload new video
- `PUT /api/v2/videos/{id}` - Update video
- `DELETE /api/v2/videos/{id}` - Delete video
- `GET /api/v2/videos/search` - Search videos

### Recording Management (v2)
- `GET /api/v2/recordings` - Get all recordings
- `POST /api/v2/recordings/start` - Start recording
- `POST /api/v2/recordings/{id}/stop` - Stop recording

### Project Management (v2)
- `GET /api/v2/projects` - Get all projects
- `POST /api/v2/projects` - Create new project
- `GET /api/v2/projects/{id}/members` - Get project members

### Example API Usage

**Create a user:**
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "password123"
  }'
```

**Get all users:**
```bash
curl http://localhost:5000/api/users
```

## Database Models

### Base Model
- `id` - Primary key
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Core Models
- **User** - User authentication and management
- **Video** - Video files with metadata
- **Recording** - Live recording sessions
- **Frame** - Individual video frames
- **Clip** - Video clips and segments
- **Segment** - Video segments
- **Device** - Recording devices
- **Project** - Project management
- **Analytics** - Usage analytics and tracking

## Development

### Adding New Models

1. Create a new model in `app/models/`
2. Import it in `app/models/__init__.py`
3. Create a schema in `app/schemas/`
4. Add API endpoints in `app/controllers/api.py`
5. Create and run migrations:
   ```bash
   flask db migrate -m "Add new model"
   flask db upgrade
   ```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

## Environment Variables

- `SECRET_KEY` - Flask secret key
- `DATABASE_URL` - Database connection string
- `FLASK_ENV` - Flask environment (development/production)
- `FLASK_DEBUG` - Debug mode (True/False)

## Docker Commands

```bash
# Build and start services
docker-compose up --build

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild specific service
docker-compose build web
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.