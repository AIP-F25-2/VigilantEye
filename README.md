# VigilantEye - AI-Powered Security Surveillance System

## 🎯 Overview

VigilantEye is a comprehensive AI-powered security surveillance system that provides real-time threat detection, person recognition, and evidence collection. The system combines computer vision, machine learning, and modern web technologies to deliver a complete security solution for monitoring and analyzing security threats.

## ✨ Key Features

### 🔍 **AI-Powered Analysis**
- **Face Recognition**: Detect and identify individuals using advanced face recognition (MTCNN + FaceNet)
- **Clothing Recognition**: Identify people based on clothing and appearance when faces aren't visible
- **Object Detection**: Detect weapons, suspicious objects, and activities using YOLOv8
- **Text Recognition**: Extract text from images using EasyOCR
- **Threat Assessment**: AI-powered threat analysis using OpenAI GPT-4 integration
- **Person Tracking**: Track individuals across multiple videos using embeddings

### 🎫 **Ticket Management**
- **Unified Interface**: Expandable table with integrated media viewer
- **Evidence Collection**: Automatic evidence gathering and organization
- **Soft Delete**: Safe ticket deletion with audit trails
- **Admin Controls**: Role-based access control (Admin/User roles)
- **Media Viewer**: Built-in image/video/audio player with download options
- **Bulk Operations**: Download all evidence as ZIP archives

### 🚀 **Deployment Ready**
- **Docker Support**: Complete containerization with multi-stage builds
- **Azure Integration**: Ready for Azure Cloud deployment (ACI, AKS, ARM templates)
- **Kubernetes**: Production-ready K8s manifests with health probes
- **CI/CD Ready**: Automated deployment pipelines with GitHub Actions
- **Local Cache**: High-performance local cache system (no Redis required)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   AI Services   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   MySQL         │    │   Model Cache    │
│   (Reverse      │    │   Database      │    │   (Pickle)       │
│    Proxy)       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Local Cache   │
                       │   & Sessions    │
                       └─────────────────┘
```

## 🗄️ Database Setup

### MySQL Database Configuration

VigilantEye uses MySQL as its primary database. Here are the setup steps:

#### Option 1: Using Docker (Recommended)

The database is automatically set up when using Docker Compose:

```bash
# Start all services including MySQL
docker-compose up -d

# Wait for MySQL to be ready (30 seconds)
sleep 30

# Setup database tables and default admin user
docker-compose exec backend python scripts/setup_database.py
```

#### Option 2: Manual MySQL Setup

If you prefer to use a local MySQL installation:

1. **Install MySQL 8.0+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install mysql-server mysql-client

   # macOS (using Homebrew)
   brew install mysql

   # Windows
   # Download from: https://dev.mysql.com/downloads/mysql/
   ```

2. **Start MySQL Service**
   ```bash
   # Ubuntu/Debian
   sudo systemctl start mysql
   sudo systemctl enable mysql

   # macOS
   brew services start mysql

   # Windows
   # Start MySQL service from Services or MySQL Workbench
   ```

3. **Create Database and User**
   ```sql
   -- Connect to MySQL as root
   mysql -u root -p

   -- Create database
   CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

   -- Create user
   CREATE USER 'vigilanteye'@'localhost' IDENTIFIED BY 'vigilanteye123';

   -- Grant privileges
   GRANT ALL PRIVILEGES ON vigilanteye.* TO 'vigilanteye'@'localhost';
   FLUSH PRIVILEGES;

   -- Exit MySQL
   EXIT;
   ```

4. **Configure Environment**
   ```bash
   # Create .env file
   cp backend/env.example .env

   # Edit .env file
   DATABASE_URL=mysql+pymysql://vigilanteye:vigilanteye123@localhost:3306/vigilanteye
   ```

5. **Initialize Database Schema**
   ```bash
   cd backend
   python scripts/setup_database.py
   ```

#### Option 3: Using Docker MySQL Only

If you want to use Docker for MySQL but run the backend locally:

1. **Start MySQL Container**
   ```bash
   docker run -d \
     --name vigilanteye-mysql \
     -e MYSQL_ROOT_PASSWORD=vigilanteye123 \
     -e MYSQL_DATABASE=vigilanteye \
     -e MYSQL_USER=vigilanteye \
     -e MYSQL_PASSWORD=vigilanteye123 \
     -p 3306:3306 \
     mysql:8.0
   ```

2. **Wait for MySQL to be ready**
   ```bash
   # Check if MySQL is ready
   docker exec vigilanteye-mysql mysqladmin ping -h localhost -u vigilanteye -pvigilanteye123
   ```

3. **Configure and Initialize**
   ```bash
   # Set environment variable
   export DATABASE_URL=mysql+pymysql://vigilanteye:vigilanteye123@localhost:3306/vigilanteye

   # Initialize database
   cd backend
   python scripts/setup_database.py
   ```

### Database Verification

After setup, verify your database is working:

```bash
# Test connection
mysql -u vigilanteye -pvigilanteye123 -h localhost vigilanteye

# Check tables
SHOW TABLES;

# Check default admin user
SELECT username, email, role FROM users WHERE role = 'admin';
```

### Database Management Commands

```bash
# Access database (Docker)
docker-compose exec mysql mysql -u vigilanteye -pvigilanteye123 vigilanteye

# Access database (Local)
mysql -u vigilanteye -pvigilanteye123 -h localhost vigilanteye

# Run migrations (create tables)
cd backend
python scripts/migrate.py create

# Backup database
mysqldump -u vigilanteye -pvigilanteye123 vigilanteye > backup.sql

# Restore database
mysql -u vigilanteye -pvigilanteye123 vigilanteye < backup.sql

# Reset database (Docker)
docker-compose exec mysql mysql -u vigilanteye -pvigilanteye123 vigilanteye -e "DROP DATABASE vigilanteye; CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Reset database (Local)
mysql -u root -p -e "DROP DATABASE vigilanteye; CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Troubleshooting Database Issues

#### Connection Refused
```bash
# Check if MySQL is running
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# Check port
netstat -tlnp | grep 3306
```

#### Authentication Failed
```bash
# Reset MySQL root password
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'newpassword';
FLUSH PRIVILEGES;
```

#### Permission Denied
```bash
# Grant proper permissions
mysql -u root -p
GRANT ALL PRIVILEGES ON vigilanteye.* TO 'vigilanteye'@'localhost';
FLUSH PRIVILEGES;
```

#### Character Set Issues
```bash
# Check current character set
mysql -u vigilanteye -pvigilanteye123 vigilanteye -e "SHOW VARIABLES LIKE 'character_set%';"

# Fix character set
mysql -u root -p -e "ALTER DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Database Schema Information

The database includes the following main tables:
- `users` - User accounts and authentication
- `videos` - Video metadata and processing status
- `tickets` - Security incident tickets
- `evidence` - Evidence files and metadata
- `person_embeddings` - AI-generated person embeddings
- `clothing_analysis` - Clothing recognition results
- `threat_assessments` - AI threat analysis results

### Database Migrations

VigilantEye uses a migration system to manage database schema changes. Currently, the project uses a script-based approach for development, with Alembic support available for production use.

#### Current Migration System

**Development Approach (Current):**
The project includes a migration script (`backend/scripts/migrate.py`) that uses SQLAlchemy's metadata to create/update database tables.

**Available Commands:**
```bash
cd backend

# Create all database tables
python scripts/migrate.py create

# Drop all database tables (⚠️ WARNING: This deletes all data!)
python scripts/migrate.py drop

# Reset database (drop and recreate)
python scripts/migrate.py reset
```

**Using Migrations:**
```bash
# After setting up your database and .env file
cd backend

# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Create all tables
python scripts/migrate.py create

# Verify tables were created
mysql -u vigilanteye -pvigilanteye123 vigilanteye -e "SHOW TABLES;"
```

**Expected Tables (14 total):**
- Core: `users`, `videos`, `storage_files`
- AI Analysis: `audio_analysis`, `face_detections`, `image_analysis`, `threat_assessments`, `face_vectors`
- Person Tracking: `person_embeddings`, `person_appearances`, `person_matches`
- Ticket Management: `tickets`, `ticket_evidence`, `ticket_activity`

#### Alembic Support (Production Recommended)

For production environments, Alembic migration support is available. The `DatabaseMigrator` class in `backend/src/utils/database_manager.py` provides Alembic integration.

**Note:** Alembic is not fully configured by default. To set up Alembic migrations:

1. **Initialize Alembic** (one-time setup):
   ```bash
   cd backend
   alembic init alembic
   ```

2. **Configure Alembic**:
   - Edit `alembic.ini` with your database URL
   - Update `alembic/env.py` to import all models and use your settings

3. **Create and Apply Migrations**:
   ```bash
   # Create new migration
   alembic revision --autogenerate -m "Description of changes"
   
   # Apply migrations
   alembic upgrade head
   
   # Check current version
   alembic current
   
   # View migration history
   alembic history
   ```

For detailed migration setup instructions, see:
- `backend/DATABASE_SETUP_GUIDE.md` - Comprehensive migration guide
- `backend/DATABASE_MIGRATION_STATUS.md` - Current migration status

#### Migration Best Practices

- **Development**: Use `migrate.py` for quick setup and testing
- **Production**: Set up Alembic for version-controlled, reversible migrations
- **Always backup** your database before running migrations in production
- **Test migrations** on a development database first
- **Review auto-generated migrations** before applying them

### Performance Optimization

For production environments, consider these MySQL optimizations:

```sql
-- Increase buffer pool size (adjust based on available RAM)
SET GLOBAL innodb_buffer_pool_size = 1G;

-- Enable query cache
SET GLOBAL query_cache_size = 64M;
SET GLOBAL query_cache_type = ON;

-- Optimize for InnoDB
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
SET GLOBAL innodb_log_file_size = 256M;
```

### Backup Strategy

```bash
# Daily automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="vigilanteye"

# Create backup
mysqldump -u vigilanteye -pvigilanteye123 $DB_NAME > $BACKUP_DIR/vigilanteye_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/vigilanteye_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "vigilanteye_*.sql.gz" -mtime +7 -delete
```

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (for containerized setup)
- **Node.js 18+** (for frontend development)
- **Python 3.11+** (for backend development)
- **Git** (for version control)

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/vigilanteye.git
   cd vigilanteye
   ```

2. **Run the setup script**
   ```bash
   chmod +x scripts/setup-dev.sh
   ./scripts/setup-dev.sh
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

### Option 2: Manual Setup

1. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Setup Database**
   ```bash
   docker-compose exec backend python scripts/setup_database.py
   ```

### Option 3: Development Setup (Windows)

1. **Use the batch file**
   ```cmd
   START_ALL.bat
   ```

2. **Or start manually**
   ```cmd
   # Terminal 1 - Backend
   cd backend
   venv\Scripts\activate
   python run.py

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

## 🛠️ Manual Start Guide

### Starting Backend Server

#### Option 1: Using Batch File (Windows - Recommended)
```cmd
cd backend
start.bat              # Normal mode
start.bat debug        # Debug mode (with verbose logging)
start-debug.bat        # Debug mode (dedicated script)
```

#### Option 2: Manual Start (Windows)
```cmd
# Navigate to backend directory
cd backend

# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run database migrations (first time only)
python scripts\migrate.py create

# Start the server (normal mode)
python run.py

# Start in debug mode (with verbose logging)
set APP_DEBUG=true
set APP_ENV=development
set LOG_LEVEL=DEBUG
python run.py
```

#### Option 3: Manual Start (Linux/Mac)
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run database migrations (first time only)
python scripts/migrate.py create

# Start the server (normal mode)
python run.py

# Start in debug mode (with verbose logging)
export APP_DEBUG=true
export APP_ENV=development
export LOG_LEVEL=DEBUG
python run.py
```

**Backend will be available at:**
- API: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/api/health

**Debug Mode Features:**
- ✅ Verbose logging (DEBUG level)
- ✅ SQL query logging (SQLAlchemy echo)
- ✅ Auto-reload on code changes
- ✅ Detailed error messages
- ✅ API documentation enabled

### Starting Frontend Server

#### Option 1: Using Batch File (Windows - Recommended)
```cmd
cd frontend
start.bat
```

#### Option 2: Manual Start (Windows)
```cmd
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start development server
npm run dev
```

#### Option 3: Manual Start (Linux/Mac)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start development server
npm run dev
```

**Frontend will be available at:**
- Application: http://localhost:5173 (Vite default port)

### Starting Both Servers (Windows)

#### Using START_ALL.bat (Easiest)
```cmd
# From project root - Normal mode
START_ALL.bat

# From project root - Debug mode
START_ALL.bat debug
```

This will:
- Check for virtual environment and dependencies
- Start backend in a new window (with debug mode if requested)
- Start frontend in a new window
- Display URLs for both servers

**To stop servers:** Use `STOP_ALL.bat` or close the server windows manually.

#### Manual Start (Two Terminals)

**Terminal 1 - Backend:**
```cmd
cd backend
venv\Scripts\activate
python run.py
```

**Terminal 2 - Frontend:**
```cmd
cd frontend
npm run dev
```

### Starting Both Servers (Linux/Mac)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python run.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Prerequisites Check

Before starting, ensure:

1. **Backend Prerequisites:**
   - ✅ Python 3.11+ installed
   - ✅ Virtual environment created (`python -m venv venv`)
   - ✅ Dependencies installed (`pip install -r requirements.txt`)
   - ✅ MySQL database running
   - ✅ Database tables created (`python scripts/migrate.py create`)
   - ✅ `.env` file configured

2. **Frontend Prerequisites:**
   - ✅ Node.js 18+ installed
   - ✅ Dependencies installed (`npm install`)

### Troubleshooting Manual Start

#### Backend Issues

**ModuleNotFoundError:**
```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Database Connection Error:**
```cmd
# Check MySQL is running
# Verify .env file has correct database credentials
# Run migrations again
python scripts\migrate.py create
```

**Port Already in Use:**
```cmd
# Change port in .env file
APP_PORT=8001

# Or kill the process using port 8000
# Windows: netstat -ano | findstr :8000
# Then: taskkill /PID <PID> /F
```

#### Frontend Issues

**Port Already in Use:**
```bash
# Vite will automatically use next available port
# Or specify port in vite.config.js
```

**Module Not Found:**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

## 🔧 Configuration

### Environment Variables

```env
# Database Configuration
MYSQL_DATABASE=vigilanteye
MYSQL_USER=vigilanteye
MYSQL_PASSWORD=vigilanteye123

# Local Cache Configuration
CACHE_DIR=storage/local_cache
CACHE_MAX_MEMORY_ITEMS=1000
CACHE_DEFAULT_TTL=3600
CACHE_CLEANUP_INTERVAL=300

# Application Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# External APIs (Optional)
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# AI Configuration
AI_DEVICE=cpu
MODEL_CACHE_ENABLED=true
```

### Python Dependencies

VigilantEye uses a comprehensive set of Python dependencies for AI/ML, video processing, database management, and web services.

#### Installing Dependencies

**Production Installation:**
```bash
cd backend
pip install -r requirements.txt
```

**Development Installation (includes testing and code quality tools):**
```bash
cd backend
pip install -r requirements-dev.txt
```

**Alternative: Using the modular requirements directory:**
```bash
cd backend

# Base dependencies only
pip install -r requirements/base.txt

# Base + Development tools
pip install -r requirements/development.txt

# Base + AI services
pip install -r requirements/base.txt -r requirements/ai_services.txt

# Base + Video processing
pip install -r requirements/base.txt -r requirements/video_processing.txt

# Base + Telegram integration
pip install -r requirements/base.txt -r requirements/telegram.txt
```

#### Dependency Categories

The project includes dependencies for:

- **Web Framework**: FastAPI, Uvicorn, Pydantic
- **Database**: SQLAlchemy, Alembic, PyMySQL, aiomysql
- **Authentication**: python-jose, passlib, bcrypt
- **Video Processing**: OpenCV, MoviePy, Pillow, NumPy
- **AI/ML Frameworks**: PyTorch, TorchVision, TorchAudio
- **Computer Vision**: Ultralytics (YOLO), FaceNet, DeepFace
- **Audio Processing**: librosa, Whisper, faster-whisper
- **OCR**: EasyOCR, PyTesseract
- **NLP/LLM**: Transformers, OpenAI, Anthropic, LangChain
- **Vector Databases**: ChromaDB, FAISS
- **Cloud Storage**: boto3 (AWS S3)
- **Telegram**: python-telegram-bot
- **Utilities**: requests, httpx, python-dotenv, psutil

For a complete list of all dependencies with versions, see `backend/requirements.txt`.

## 🌐 Azure Cloud Deployment

### Prerequisites
- **Azure CLI** installed and configured
- **Docker** installed locally
- **Azure subscription** with appropriate permissions

### Option 1: Automated Deployment

1. **Run the deployment script**
```bash
   chmod +x scripts/deploy-azure.sh
   ./scripts/deploy-azure.sh
   ```

2. **Follow the prompts** for Azure login and resource creation

### Option 2: Manual Azure Deployment

#### Using Azure Container Instances

1. **Create Resource Group**
   ```bash
   az group create --name vigilanteye-rg --location eastus
   ```

2. **Deploy ARM Template**
```bash
   az deployment group create \
     --resource-group vigilanteye-rg \
     --template-file azure/arm-template.json \
     --parameters appName=vigilanteye environment=production
   ```

3. **Build and Push Images**
```bash
   # Login to ACR
   az acr login --name your-acr-name

   # Build and push
   docker build -t your-acr-name.azurecr.io/vigilanteye-backend:latest ./backend
   docker push your-acr-name.azurecr.io/vigilanteye-backend:latest

   docker build -t your-acr-name.azurecr.io/vigilanteye-frontend:latest ./frontend
   docker push your-acr-name.azurecr.io/vigilanteye-frontend:latest
```

4. **Deploy Containers**
```bash
   az container create \
     --resource-group vigilanteye-rg \
     --name vigilanteye-backend \
     --image your-acr-name.azurecr.io/vigilanteye-backend:latest \
     --cpu 2 --memory 4 --ports 8000 \
     --environment-variables DATABASE_URL=your-db-url
   ```

#### Using Azure Kubernetes Service

1. **Create AKS Cluster**
   ```bash
   az aks create \
     --resource-group vigilanteye-rg \
     --name vigilanteye-aks \
     --node-count 2 \
     --enable-addons monitoring
   ```

2. **Get Credentials**
```bash
   az aks get-credentials --resource-group vigilanteye-rg --name vigilanteye-aks
   ```

3. **Deploy with Kubernetes**
```bash
kubectl apply -f azure/kubernetes.yaml
```

### Azure Configuration Files

- **ARM Template**: `azure/arm-template.json` - Complete Azure infrastructure
- **Kubernetes**: `azure/kubernetes.yaml` - K8s deployment manifests
- **Container Instances**: `azure/container-instances.yaml` - ACI configuration

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ --cov=src --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Performance Tests
```bash
cd backend
python tests/performance/benchmark.py
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- **Basic**: `GET /api/health`
- **Detailed**: `GET /api/health/detailed`
- **Readiness**: `GET /api/health/ready`
- **Liveness**: `GET /api/health/live`

### Monitoring Features
- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times
- **Health Monitoring**: Database, cache, AI services
- **Alerting**: Automated alerts for system issues

## 🛠️ Development

### Project Structure
```
vigilanteye/
├── backend/              # FastAPI backend
│   ├── src/
│   │   ├── api/         # API endpoints
│   │   ├── services/    # Business logic
│   │   ├── models/      # Database models
│   │   ├── repositories/# Data access
│   │   └── utils/       # Utilities
│   ├── tests/           # Test files
│   ├── requirements/    # Dependencies
│   └── Dockerfile       # Backend container
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/       # React pages
│   │   ├── components/  # React components
│   │   ├── services/    # API services
│   │   └── store/       # State management
│   └── Dockerfile       # Frontend container
├── azure/               # Azure deployment configs
├── scripts/             # Deployment scripts
├── docker-compose.yml   # Development setup
└── docker-compose.prod.yml # Production setup
```

### Useful Commands

```bash
# Quick Start (Windows)
START_ALL.bat                           # Start both backend and frontend
START_ALL.bat debug                     # Start both in debug mode
STOP_ALL.bat                            # Stop both backend and frontend

# Backend Commands
cd backend
start.bat                               # Start backend (Windows)
start.bat debug                         # Start backend in debug mode
start-debug.bat                         # Start backend in debug mode (dedicated)
.\venv\Scripts\activate                 # Activate virtual environment
python run.py                           # Start backend server
python scripts\migrate.py create        # Create database tables
python scripts\migrate.py reset         # Reset database (⚠️ deletes data)

# Debug Mode (Windows)
set APP_DEBUG=true && set LOG_LEVEL=DEBUG && python run.py

# Frontend Commands
cd frontend
start.bat                               # Start frontend (Windows)
npm install                             # Install dependencies
npm run dev                             # Start development server
npm run build                           # Build for production

# Development
docker-compose up -d                    # Start all services
docker-compose logs -f                  # View logs
docker-compose restart backend          # Restart backend
docker-compose exec backend bash        # Access backend container

# Database
docker-compose exec mysql mysql -u vigilanteye -pvigilanteye123 vigilanteye
docker-compose exec backend python scripts/setup_database.py
docker-compose exec backend python scripts/migrate.py create    # Run migrations
docker-compose exec backend python scripts/migrate.py reset     # Reset database (⚠️ deletes data)

# Cache Management
docker-compose exec backend python -c "from src.services.local_cache import get_cache; print(get_cache().get_stats())"

# Testing
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access**: Admin and User roles
- **Rate Limiting**: Per-user and per-IP limits
- **Input Sanitization**: XSS and injection prevention
- **File Upload Validation**: Secure file handling
- **CORS Protection**: Configurable allowed origins

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh token

### Video Processing
- `POST /api/video/upload` - Upload video
- `GET /api/video/status/{id}` - Get processing status
- `GET /api/videos` - List videos

### Ticket Management
- `GET /api/tickets` - List tickets
- `POST /api/tickets` - Create ticket
- `GET /api/tickets/{id}` - Get ticket details
- `PUT /api/tickets/{id}` - Update ticket

### Health & Monitoring
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed system status
- `GET /api/metrics` - Application metrics

## 🚨 Troubleshooting

### Common Issues

#### Docker Issues
```bash
# If containers fail to start
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check container logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
```

#### Database Issues
```bash
# Check database status
docker-compose exec postgres pg_isready -U vigilanteye -d vigilanteye

# Reset database
docker-compose exec postgres psql -U vigilanteye -d vigilanteye -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Run database setup
docker-compose exec backend python scripts/setup_database.py
```

#### Cache Issues
```bash
# Check cache status
docker-compose exec backend python -c "from src.services.local_cache import get_cache; print(get_cache().get_stats())"

# Clear cache
docker-compose exec backend python -c "from src.services.local_cache import get_cache; get_cache().clear()"
```

## 📈 Performance

### Response Time Targets
- **API Endpoints**: < 200ms average
- **Database Queries**: < 100ms average
- **File Uploads**: < 5s for 100MB files
- **Page Load**: < 2s for frontend pages

### Scalability Features
- **Horizontal Scaling**: Multi-instance deployment
- **Database**: Connection pooling and read replicas
- **Caching**: Local cache with memory + disk persistence
- **CDN**: Static asset delivery optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub discussions for questions
- **Email**: Contact the development team

## 🎯 Roadmap

### Planned Features
- **E2E Testing**: Playwright integration
- **Chaos Engineering**: Fault injection testing
- **A/B Testing**: Feature flag testing
- **ML Testing**: AI model testing framework

### Monitoring Enhancements
- **Distributed Tracing**: OpenTelemetry integration
- **Custom Dashboards**: Grafana dashboards
- **Advanced Alerting**: Sophisticated alerting rules
- **Analytics**: Usage analytics and insights

---

**Last Updated**: 2024-01-01  
**Version**: 1.0.0  
**Maintainer**: VigilantEye Development Team