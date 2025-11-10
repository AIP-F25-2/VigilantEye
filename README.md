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

