# VigilantEye - AI-Powered Surveillance System

An intelligent multi-camera surveillance system with AI-powered threat detection, automated alerting, and comprehensive reporting.

## 🎯 Features

### AI Capabilities
- **Face & Person Detection** - Identify and track individuals with ReID
- **Scene Understanding** - Detailed environmental context analysis
- **Object Detection** - Detect suspicious items and weapons
- **Speech-to-Text** - Transcribe audio from surveillance footage
- **Audio Classification** - Detect gunshots, screams, alarms, etc.
- **LLM Analysis** - Intelligent threat assessment using local LLM

### Software Modules
- **Authentication & Access Control** - JWT-based auth with staff/admin roles
- **Video Processing** - Upload videos or stream from live cameras
- **Storage Management** - Hierarchical storage with TTL-based cleanup
- **Ticket Management** - Incident tracking with auto-escalation
- **Telegram Integration** - Real-time alerts to first responders
- **Report Generation** - Comprehensive PDF reports with evidence

### User Interface
- **Login/SignUp** - Secure authentication
- **Home** - Video upload and live camera streaming
- **Video Directory** - Manage and analyze stored videos
- **Tickets** - View and manage security incidents
- **Analytics** - System health and performance metrics

## 🏗️ Architecture

```
VigilantEye/
├── backend/          # Flask API + AI Services
├── frontend/         # React + TypeScript UI
├── docker-compose.yml
└── .github/workflows/ # CI/CD pipelines
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. Clone Repository

```bash
git clone <repository-url>
cd VigilantEye
```

### 2. Start Infrastructure Services

```bash
docker-compose up -d
```

This starts MySQL, Redis, and ChromaDB.

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/base.txt
pip install -r requirements/ai_services.txt
# For development tooling
pip install -r requirements/development.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
alembic upgrade head

# Start Flask API
flask --app src.app:create_app run --host=0.0.0.0 --port=5000
# or
python -m flask --app src.app:create_app run --host=0.0.0.0 --port=5000
```

### 4. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

### 5. Start Celery Workers (separate terminals)

```bash
cd backend
source venv/bin/activate

# Worker
celery -A src.celery_app:create_celery_app worker --loglevel=info

# Beat (enable ENABLE_BEAT=true only after required tasks exist)
# celery -A src.celery_app:create_celery_app beat --loglevel=info
```

### 6. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000/api
- **Health Check**: http://localhost:5000/health

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended for AI models)
- 50GB disk space (for AI models, videos, database)

### Quick Start with Docker

**1. Clone and Configure:**

```bash
git clone <repository-url>
cd VigilantEye
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files with your configuration
```

**2. Start All Services:**

```bash
make up
# Or: docker-compose up -d
```

**3. Run Database Migrations:**

```bash
make db-migrate
# Or: docker-compose exec backend alembic upgrade head
```

**4. Seed Test Data (Optional):**

```bash
make db-seed
# Or: docker-compose exec backend python scripts/seed_test_data.py
```

**5. Access Application:**

- Frontend: http://localhost:80
- Backend API: http://localhost:80/api
- Health Check: http://localhost:80/health
- Metrics: http://localhost:80/metrics

### Services

**Infrastructure Services:**

- **MySQL 8.0**: Primary database (port 3306)
- **Redis 7**: Cache and message broker (port 6379)
- **ChromaDB**: Vector database for embeddings (port 8000)
- **Ollama**: Local LLM inference (port 11434)

**Application Services:**

- **Backend (Flask)**: REST API and WebSocket server (port 5000)
- **Celery Worker**: Async task processing (AI analysis, cleanup)
- **Celery Beat**: Scheduled tasks (TTL cleanup, auto-close, escalation)
- **Nginx**: Reverse proxy and frontend server (ports 80, 443)

### Makefile Commands

**Development:**

- `make up` - Start all services
- `make down` - Stop all services
- `make logs` - View logs from all services
- `make logs-backend` - View backend logs only
- `make restart` - Restart all services
- `make ps` - List running containers

**Database:**

- `make db-migrate` - Run database migrations
- `make db-seed` - Seed test data
- `make db-reset` - Reset database to clean state
- `make shell-db` - Open MySQL shell

**Testing:**

- `make test` - Run all tests (backend + frontend)
- `make test-backend` - Run backend tests only
- `make test-frontend` - Run frontend tests only

**Maintenance:**

- `make build` - Build all images
- `make rebuild` - Rebuild without cache
- `make clean` - Remove all containers and volumes (WARNING: data loss)
- `make prune` - Clean up unused Docker resources

**Debugging:**

- `make shell-backend` - Open shell in backend container
- `make pull-models` - Pre-download AI models

### Production Deployment

**1. Configure Production Environment:**

```bash
cp .env.production .env
# Edit .env with production values (strong passwords, actual domains)
```

**2. Build Production Images:**

```bash
make rebuild
```

**3. Start Services:**

```bash
make up
```

**4. Configure SSL (Optional):**

- Place SSL certificates in `nginx/ssl/`
- Update nginx.conf to enable HTTPS
- Restart Nginx: `docker-compose restart nginx`

**5. Monitor Health:**

- Check health: `curl http://localhost/health`
- Check readiness: `curl http://localhost/health/ready`
- View metrics: `curl http://localhost/metrics`

### Troubleshooting

**Services won't start:**

- Check logs: `make logs`
- Check service status: `make ps`
- Verify ports not in use: `netstat -an | grep 3306` (MySQL), `grep 6379` (Redis)
- Check Docker resources: `docker system df`

**Backend fails health check:**

- Check backend logs: `make logs-backend`
- Verify database connection: `make shell-db`
- Check Redis: `docker-compose exec redis redis-cli ping`
- Check ChromaDB: `curl http://localhost:8000/api/v1/heartbeat`

**Celery worker not processing tasks:**

- Check worker logs: `docker-compose logs -f celery-worker`
- Verify Redis connection (Celery uses Redis as broker)
- Check worker is registered: `docker-compose exec celery-worker celery -A src.celery_app inspect active`

**Nginx 502 Bad Gateway:**

- Check backend is running: `docker-compose ps backend`
- Check backend health: `curl http://localhost:5000/health`
- Review Nginx logs: `docker-compose logs nginx`
- Verify upstream configuration in nginx.conf

**Out of disk space:**

- Check Docker disk usage: `docker system df`
- Clean up: `make prune`
- Remove old images: `docker image prune -a`
- Check storage volume: `docker volume inspect vigilanteye_backend_storage`

**AI models not downloading:**

- Check Ollama is running: `docker-compose ps ollama`
- Pull model manually: `docker-compose exec ollama ollama pull llama3.2:1b`
- Check disk space (models are 1-5GB each)
- Review backend logs for download errors

## Testing

### Backend Tests

**Run all tests with coverage:**

```bash
cd backend
pytest
```

**Run specific test types:**

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only (slower)
pytest -m integration

# Specific test file
pytest tests/unit/test_auth_service.py

# With coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Test Structure:**

- `tests/unit/` - Unit tests for services and AI modules (18 files)
- `tests/integration/` - Integration tests for API endpoints (8 files)
- `tests/performance/` - Locust performance tests
- `tests/api/` - Postman API collection

**Coverage Target:** 80% minimum (enforced by pytest.ini)

### Frontend Tests

**Run all tests with coverage:**

```bash
cd frontend
npm run test:coverage
```

**Run in watch mode:**

```bash
npm run test
```

**Test Structure:**

- `src/__tests__/components/` - Component tests (24 files)
- `src/__tests__/pages/` - Page tests (5 files)
- `src/__tests__/hooks/` - Hook tests (5 files)
- `src/__tests__/services/` - Service tests (5 files)

**Coverage Target:** 80% minimum (enforced by vite.config.ts)

### Integration Tests (Docker)

**Run with Docker Compose:**

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

**Cleanup:**

```bash
docker-compose -f docker-compose.test.yml down -v
```

### Performance Tests

**Run Locust tests:**

```bash
cd backend

# Start backend
python -m flask run &

# Run Locust (100 users, 60s)
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s --html performance-report.html

# View report
open performance-report.html
```

### API Tests (Postman/Newman)

**Run with Newman:**

```bash
cd backend/tests/api
newman run postman_collection.json -e dev.postman_environment.json --reporters cli,html
```

### Code Quality (SonarQube)

**Run SonarQube analysis:**

```bash
# Install sonar-scanner
npm install -g sonar-scanner

# Run analysis
sonar-scanner

# View results at https://sonarcloud.io
```

**Quality Gates:**

- Coverage: ≥80%
- Duplications: <3%
- Maintainability: A rating
- Reliability: A rating
- Security: A rating

## 📦 Technology Stack

### Backend
- Flask 3.0 - Web framework
- Celery - Async task processing
- SQLAlchemy - ORM
- MySQL 8.0 - Primary database
- Redis - Cache & message broker
- ChromaDB - Vector database
- YOLOv8, Whisper, CLIP - AI models
- Ollama - Local LLM inference

### Frontend
- React 18 - UI library
- TypeScript - Type safety
- Vite - Build tool
- Tailwind CSS - Styling
- TanStack Query - Data fetching
- Zustand - State management

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ --cov=src --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm run test:coverage
```

## 📚 Documentation

- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)
- API Documentation: Coming soon
- Architecture Guide: Coming soon

## 🔒 Security

- JWT authentication with refresh tokens
- bcrypt password hashing
- Rate limiting on auth endpoints
- CORS configuration
- Input validation and sanitization

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

## 📧 Contact

For questions or support, please open an issue.

