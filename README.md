# Flask REST API with SQLAlchemy and Docker

A complete Flask REST API structure with models, controllers, SQLAlchemy ORM, and Docker support.

## Project Structure

```
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # Base model with common fields
│   │   └── user.py              # User model
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── main.py              # Main routes (health check)
│   │   └── api.py               # API endpoints
│   └── schemas/
│       ├── __init__.py
│       └── user_schema.py       # Marshmallow schemas for validation
├── migrations/                   # Database migrations
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml           # Docker Compose setup
├── run.py                       # Application entry point
└── env.example                  # Environment variables template
```

## Features

- **Flask REST API** with proper structure
- **SQLAlchemy ORM** for database operations
- **PostgreSQL** database with Docker
- **Flask-Migrate** for database migrations
- **Marshmallow** for data validation and serialization
- **CORS** support for cross-origin requests
- **Docker** and **Docker Compose** setup
- **Base Model** with common fields (id, created_at, updated_at)
- **User Model** with authentication support

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd <your-repo>
   cp env.example .env
   ```

2. **Start the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the API:**
   - API Base URL: `http://localhost:5000`
   - Health Check: `http://localhost:5000/health`
   - API Endpoints: `http://localhost:5000/api/`

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize database:**
   ```bash
   flask db init
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

### User Management
- `GET /api/users` - Get all users
- `GET /api/users/{id}` - Get user by ID
- `POST /api/users` - Create new user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

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

### User Model
- `username` - Unique username
- `email` - Unique email address
- `password_hash` - Hashed password
- `is_active` - Account status

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