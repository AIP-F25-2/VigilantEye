# VigilantEye Backend

Flask-based backend API with AI-powered video analysis.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Runtime dependencies (aggregated)
pip install -r requirements.txt

# Alternatively install the segmented files
pip install -r requirements/base.txt
pip install -r requirements/ai_services.txt

# Development tooling
pip install -r requirements/development.txt
```

Use the aggregated `requirements.txt` when you need the complete runtime stack (API, Celery workers, and AI services). Install from the segmented files if you only require core services, want to speed up CI runs, or need to avoid the larger AI-related dependencies during development.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start Services (Docker Compose)

```bash
# From project root
docker-compose up -d mysql redis chromadb
```

### 5. Run Database Migrations

```bash
flask db upgrade
```

### 6. Start Application

```bash
# Flask API
flask --app src.app:create_app run --host=0.0.0.0 --port=5000
# or
python -m flask --app src.app:create_app run --host=0.0.0.0 --port=5000

# Celery Worker (separate terminal)
celery -A src.celery_app:create_celery_app worker --loglevel=info

# Celery Beat (enable ENABLE_BEAT=true only after required tasks exist)
# celery -A src.celery_app:create_celery_app beat --loglevel=info
```

> **MySQL credentials:** The default docker-compose configuration uses `MYSQL_USER=vigilanteye_user` and `MYSQL_PASSWORD=vigilanteye_pass`. Update these values in `.env` and `docker-compose.yml` for production deployments.

## Project Structure

```
backend/
├── src/
│   ├── api/          # REST API endpoints
│   ├── services/     # Business logic
│   ├── ai_modules/   # AI processing
│   ├── models/       # Database models
│   ├── utils/        # Utilities
│   ├── config/       # Configuration
│   └── tasks/        # Celery tasks
├── storage/          # Local file storage
├── models_cache/     # Downloaded AI models
├── tests/            # Test suite
└── requirements/     # Dependencies
```

## API Documentation

API will be available at `http://localhost:5000/api`

Health check: `http://localhost:5000/health`

## Testing

```bash
pytest tests/ --cov=src --cov-report=html
```

## Code Quality

```bash
black src/
flake8 src/
isort src/
mypy src/
```

