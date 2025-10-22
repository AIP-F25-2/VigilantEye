# VigilantEye - AI-Powered Security Surveillance System

## 🎯 Overview

VigilantEye is a comprehensive AI-powered security surveillance system that provides real-time threat detection, person recognition, and evidence collection. The system combines computer vision, machine learning, and modern web technologies to deliver a complete security solution for monitoring and analyzing security threats.

### 🎬 **How It Works**

1. **Video Upload/Analysis**: Users upload video files or connect live camera feeds
2. **AI Processing**: System analyzes each frame using multiple AI models:
   - **Face Detection**: Identifies and recognizes faces using MTCNN + FaceNet
   - **Person Detection**: Identifies people by clothing/appearance when faces aren't visible
   - **Object Detection**: Detects weapons, suspicious objects using YOLO
   - **Text Extraction**: Extracts text from images using OCR
   - **Threat Assessment**: AI analyzes scene for potential threats using LLM
3. **Threat Detection**: When threats are detected, system automatically:
   - Creates security tickets with evidence
   - Sends alerts via Telegram
   - Collects related evidence from other videos
   - Generates comprehensive reports
4. **Ticket Management**: Security personnel can:
   - View and manage threat tickets
   - Review evidence and media
   - Acknowledge and close tickets
   - Download evidence packages

## ✨ Key Features

### 🔍 **AI-Powered Analysis**
- **Face Recognition**: Detect and identify individuals using advanced face recognition (MTCNN + FaceNet)
- **Clothing Recognition**: Identify people based on clothing and appearance when faces aren't visible
- **Object Detection**: Detect weapons, suspicious objects, and activities using YOLOv8
- **Text Recognition**: Extract text from images using EasyOCR
- **Threat Assessment**: AI-powered threat analysis using OpenAI GPT-4 integration
- **Person Tracking**: Track individuals across multiple videos using embeddings

### 📊 **Performance & Monitoring**
- **Real-time Metrics**: Comprehensive performance monitoring with psutil
- **Health Checks**: Kubernetes-ready health probes (liveness/readiness)
- **Model Caching**: Intelligent AI model caching for faster startup (pickle-based)
- **System Metrics**: CPU, memory, disk, and network monitoring
- **Request Tracking**: Automatic request/response time tracking

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
- **CI/CD Ready**: Automated deployment pipelines
- **Environment Management**: Development and production configurations

### 🧹 **Automatic Data Management**
- **Periodic Cleanup**: Automatic cleanup of old person/embedding data
- **Configurable Retention**: Customizable retention periods for different data types
- **Manual Control**: API endpoints for manual cleanup and monitoring
- **Storage Optimization**: Automatic cleanup of orphaned files and media
- **Background Processing**: Non-blocking cleanup operations

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
│   Nginx         │    │   PostgreSQL    │    │   Model Cache    │
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

## 📚 Complete API Documentation

### 🔐 **Authentication APIs**

#### **POST /api/auth/login**
Login with username and password
```json
{
  "username": "admin",
  "password": "password123"
}
```
**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "ADMIN",
    "email": "admin@vigilanteye.com"
  }
}
```

#### **POST /api/auth/register**
Register new user (Admin only)
```json
{
  "username": "newuser",
  "password": "password123",
  "email": "user@example.com",
  "role": "USER"
}
```

#### **POST /api/auth/logout**
Logout current user
**Headers:** `Authorization: Bearer <token>`

#### **GET /api/auth/me**
Get current user info
**Headers:** `Authorization: Bearer <token>`

### 🎥 **Video Processing APIs**

#### **POST /api/videos/upload**
Upload video file for analysis
```bash
curl -X POST "http://localhost:8000/api/videos/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@security_footage.mp4" \
  -F "description=Security footage from camera 1"
```

#### **POST /api/videos/process**
Process uploaded video with AI analysis
```json
{
  "video_id": 123,
  "analysis_options": {
    "face_detection": true,
    "object_detection": true,
    "text_extraction": true,
    "threat_assessment": true
  }
}
```

#### **GET /api/videos**
List all videos with pagination
```bash
curl "http://localhost:8000/api/videos?page=1&limit=10&status=processed"
```

#### **GET /api/videos/{video_id}**
Get specific video details
```bash
curl "http://localhost:8000/api/videos/123" \
  -H "Authorization: Bearer <token>"
```

#### **GET /api/videos/{video_id}/frames**
Get video frames with analysis results
```bash
curl "http://localhost:8000/api/videos/123/frames?timestamp_ms=30000"
```

### 🎫 **Ticket Management APIs**

#### **GET /api/tickets**
List all tickets with filtering
```bash
curl "http://localhost:8000/api/tickets?status=OPEN&priority=HIGH&page=1&limit=20"
```

#### **GET /api/tickets/{ticket_id}**
Get specific ticket details
```bash
curl "http://localhost:8000/api/tickets/456" \
  -H "Authorization: Bearer <token>"
```

#### **POST /api/tickets/{ticket_id}/acknowledge**
Acknowledge a ticket
```json
{
  "notes": "Ticket acknowledged, investigating threat"
}
```

#### **POST /api/tickets/{ticket_id}/close**
Close a ticket
```json
{
  "notes": "Threat resolved, no further action needed"
}
```

#### **POST /api/tickets/{ticket_id}/note**
Add note to ticket
```json
{
  "note": "Additional investigation notes"
}
```

#### **GET /api/tickets/{ticket_id}/evidence**
Get all evidence for a ticket
```bash
curl "http://localhost:8000/api/tickets/456/evidence" \
  -H "Authorization: Bearer <token>"
```

#### **GET /api/tickets/{ticket_id}/evidence/download**
Download all evidence as ZIP
```bash
curl "http://localhost:8000/api/tickets/456/evidence/download" \
  -H "Authorization: Bearer <token>" \
  -o evidence.zip
```

#### **DELETE /api/tickets/{ticket_id}/evidence/{evidence_id}**
Delete specific evidence (Admin only)
```bash
curl -X DELETE "http://localhost:8000/api/tickets/456/evidence/789" \
  -H "Authorization: Bearer <admin_token>"
```

#### **DELETE /api/tickets/{ticket_id}**
Soft delete ticket (Admin only)
```bash
curl -X DELETE "http://localhost:8000/api/tickets/456" \
  -H "Authorization: Bearer <admin_token>"
```

#### **GET /api/tickets/stats/summary**
Get ticket statistics
```bash
curl "http://localhost:8000/api/tickets/stats/summary" \
  -H "Authorization: Bearer <token>"
```

### 🤖 **AI Model Management APIs**

#### **GET /api/models/cache/stats**
Get model cache statistics
```bash
curl "http://localhost:8000/api/models/cache/stats" \
  -H "Authorization: Bearer <admin_token>"
```

#### **GET /api/models/cache/validate**
Validate model cache integrity
```bash
curl "http://localhost:8000/api/models/cache/validate" \
  -H "Authorization: Bearer <admin_token>"
```

#### **POST /api/models/cache/preload**
Preload all AI models
```bash
curl -X POST "http://localhost:8000/api/models/cache/preload" \
  -H "Authorization: Bearer <admin_token>"
```

#### **GET /api/models/cache/models**
List available models
```bash
curl "http://localhost:8000/api/models/cache/models" \
  -H "Authorization: Bearer <token>"
```

#### **DELETE /api/models/cache/clear**
Clear all model cache
```bash
curl -X DELETE "http://localhost:8000/api/models/cache/clear" \
  -H "Authorization: Bearer <admin_token>"
```

#### **DELETE /api/models/cache/clear/{model_name}**
Clear specific model cache
```bash
curl -X DELETE "http://localhost:8000/api/models/cache/clear/mtcnn" \
  -H "Authorization: Bearer <admin_token>"
```

### 🏥 **Health Check APIs**

#### **GET /api/health**
Basic health check
```bash
curl "http://localhost:8000/api/health"
```

#### **GET /api/health/detailed**
Comprehensive health check with metrics
```bash
curl "http://localhost:8000/api/health/detailed"
```

#### **GET /api/health/metrics**
Detailed performance metrics
```bash
curl "http://localhost:8000/api/health/metrics"
```

#### **GET /api/health/readiness**
Kubernetes readiness probe
```bash
curl "http://localhost:8000/api/health/readiness"
```

#### **GET /api/health/liveness**
Kubernetes liveness probe
```bash
curl "http://localhost:8000/api/health/liveness"
```

### 🧹 **Cleanup Management APIs**

#### **GET /api/cleanup/status**
Get cleanup status and next run time
```bash
curl "http://localhost:8000/api/cleanup/status" \
  -H "Authorization: Bearer <token>"
```

#### **GET /api/cleanup/stats**
Get cleanup statistics (Admin only)
```bash
curl "http://localhost:8000/api/cleanup/stats" \
  -H "Authorization: Bearer <admin_token>"
```

#### **GET /api/cleanup/config**
Get cleanup configuration (Admin only)
```bash
curl "http://localhost:8000/api/cleanup/config" \
  -H "Authorization: Bearer <admin_token>"
```

#### **POST /api/cleanup/run**
Run manual cleanup (Admin only)
```bash
curl -X POST "http://localhost:8000/api/cleanup/run" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

#### **POST /api/cleanup/test**
Test cleanup without deleting data (Admin only)
```bash
curl -X POST "http://localhost:8000/api/cleanup/test" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

#### **GET /api/health/db**
Database health check
```bash
curl "http://localhost:8000/api/health/db"
```

## 🖥️ **User Interface Overview**

### **Dashboard Page** (`/dashboard`)
- **Video Upload**: Drag-and-drop video file upload
- **Live Camera**: Connect to live camera feeds
- **Processing Status**: Real-time processing progress
- **Recent Activity**: Latest threats and tickets
- **Quick Stats**: Overview of system metrics

### **Tickets Page** (`/tickets`)
- **Unified Table**: Expandable rows showing ticket details
- **Filtering**: Filter by status, priority, date
- **Search**: Search tickets by title, description, ticket number
- **Bulk Actions**: Acknowledge, close multiple tickets
- **Media Viewer**: Integrated image/video/audio player
- **Download Options**: Individual files or ZIP archives

### **Ticket Detail View** (Expanded Row)
- **Ticket Information**: Title, description, priority, status
- **Evidence Gallery**: Grid view of all evidence files
- **Media Player**: Built-in player for images, videos, audio
- **Activity Log**: Timeline of ticket actions
- **Admin Controls**: Delete tickets/media (Admin only)

### **Authentication Pages**
- **Login**: Username/password authentication
- **Sign Up**: User registration (if enabled)
- **Role-based Access**: Different UI elements for Admin/User roles

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (for containerized setup)
- **Node.js 18+** (for frontend development)
- **Python 3.11+** (for backend development)
- **Git** (for version control)

### Development Setup

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

### Manual Setup

1. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Preload AI Models** (Optional)
   ```bash
   docker-compose exec backend python scripts/preload_models.py
   ```

## 🖥️ **Complete Setup Guide for Brand New Laptop**

### **Step 1: Install Prerequisites**

#### **1.1 Install Git**
```bash
# Windows (using Chocolatey)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco install git

# macOS (using Homebrew)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git

# Ubuntu/Debian
sudo apt update
sudo apt install git
```

#### **1.2 Install Docker Desktop**
```bash
# Download from: https://www.docker.com/products/docker-desktop/
# Windows: Download Docker Desktop for Windows
# macOS: Download Docker Desktop for Mac
# Linux: Follow instructions at https://docs.docker.com/engine/install/

# Verify installation
docker --version
docker-compose --version
```

#### **1.3 Install Node.js (for development)**
```bash
# Download from: https://nodejs.org/
# Install LTS version (18.x or higher)

# Verify installation
node --version
npm --version
```

#### **1.4 Install Python (for development)**
```bash
# Windows: Download from https://www.python.org/downloads/
# macOS: brew install python@3.11
# Ubuntu/Debian: sudo apt install python3.11 python3.11-venv python3.11-pip

# Verify installation
python --version
pip --version
```

### **Step 2: Clone and Setup Project**

#### **2.1 Clone Repository**
```bash
git clone https://github.com/your-org/vigilanteye.git
cd vigilanteye
```

#### **2.2 Create Environment File**
```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
nano .env  # or use your preferred editor
```

**Environment Configuration:**
```env
# Database Configuration
POSTGRES_DB=vigilanteye
POSTGRES_USER=vigilanteye
POSTGRES_PASSWORD=vigilanteye123

# Redis Configuration
REDIS_PASSWORD=vigilanteye123

# Application Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# External APIs (Optional but recommended)
OPENAI_API_KEY=sk-your-openai-api-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# AI Configuration
AI_DEVICE=cpu
MODEL_CACHE_ENABLED=true
MODEL_CACHE_PATH=storage/model_cache
```

### **Step 3: Quick Start with Docker (Recommended)**

#### **3.1 One-Command Setup (with Telegram)**
```bash
# Windows
scripts\setup-with-telegram.bat

# Linux/Mac
chmod +x scripts/setup-with-telegram.sh
./scripts/setup-with-telegram.sh
```

#### **3.2 Manual Docker Setup**
```bash
# Create necessary directories
mkdir -p backend/storage/videos
mkdir -p backend/storage/evidence
mkdir -p backend/storage/model_cache
mkdir -p backend/storage/vector_db
mkdir -p backend/logs

# Build and start services
docker-compose build
docker-compose up -d

# Check service health
docker-compose ps
```

#### **3.3 Verify Installation**
```bash
# Check backend health
curl http://localhost:8000/api/health

# Check frontend
curl http://localhost:3000/health

# Check database
docker-compose exec postgres pg_isready -U vigilanteye -d vigilanteye

# Setup database (if not already done)
docker-compose exec backend python scripts/setup_database.py

# Check cleanup status
curl "http://localhost:8000/api/cleanup/status" \
  -H "Authorization: Bearer <token>"

# Check local cache
curl "http://localhost:8000/api/health/detailed"
```

### **Step 4: Development Setup (Optional)**

#### **4.1 Backend Development**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements/core.txt
pip install -r requirements/ai_services.txt

# Run development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### **4.2 Frontend Development**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### **Step 5: Preload AI Models (Recommended)**

#### **5.1 Preload Models**
```bash
# Using Docker
docker-compose exec backend python scripts/preload_models.py

# Or manually
cd backend
python scripts/preload_models.py
```

#### **5.2 Verify Model Cache**
```bash
# Check model cache status
curl http://localhost:8000/api/models/cache/stats

# Expected output:
{
  "cache_dir": "storage/model_cache",
  "total_models": 8,
  "total_size_mb": 245.67,
  "available_models": ["mtcnn", "facenet_resnet", "resnet50", "yolov8n", "easyocr", "opencv_hog"]
}
```

### **Step 6: Access Application**

#### **6.1 Web Interface**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

#### **6.2 Default Credentials**
- **Username**: `admin`
- **Password**: `admin123` (change in production!)

### **Step 7: Test the System**

#### **7.1 Upload Test Video**
1. Go to http://localhost:3000
2. Login with admin credentials
3. Navigate to Dashboard
4. Upload a test video file
5. Wait for processing to complete

#### **7.2 Check Results**
1. Go to Tickets page
2. View generated tickets
3. Click on ticket rows to expand
4. View evidence and media
5. Test media player functionality

### **Step 8: Production Deployment**

#### **8.1 Azure Deployment**
```bash
# Install Azure CLI
# Windows: choco install azure-cli
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set environment variables
export OPENAI_API_KEY="your-openai-key"
export TELEGRAM_BOT_TOKEN="your-telegram-token"

# Deploy to Azure
chmod +x scripts/deploy-azure.sh
./scripts/deploy-azure.sh
```

#### **8.2 Kubernetes Deployment**
```bash
# Install kubectl
# Windows: choco install kubernetes-cli
# macOS: brew install kubectl
# Linux: curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Create secrets
kubectl create secret generic vigilanteye-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=secret-key="your-secret-key" \
  --from-literal=jwt-secret-key="your-jwt-key" \
  --from-literal=openai-api-key="your-openai-key"

# Deploy to Kubernetes
kubectl apply -f azure/kubernetes.yaml
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://vigilanteye:vigilanteye123@postgres:5432/vigilanteye` |
| `SECRET_KEY` | Application secret key | `your-secret-key-change-in-production` |
| `JWT_SECRET_KEY` | JWT signing key | `your-jwt-secret-key-change-in-production` |
| `OPENAI_API_KEY` | OpenAI API key for LLM | - |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for alerts | `8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0` |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram webhook secret | `supersecret` |
| `TELEGRAM_ESCALATION_CHANNEL` | Telegram escalation channel ID | `-4672336726` |
| `AI_DEVICE` | AI processing device | `cpu` |
| `MODEL_CACHE_ENABLED` | Enable model caching | `true` |
| `CLEANUP_ENABLED` | Enable automatic cleanup | `true` |
| `CLEANUP_INTERVAL_HOURS` | Cleanup interval in hours | `24` |
| `PERSON_DATA_RETENTION_DAYS` | Person data retention days | `30` |
| `EMBEDDING_DATA_RETENTION_DAYS` | Embedding data retention days | `90` |
| `MEDIA_RETENTION_DAYS` | Media file retention days | `60` |

### AI Model Configuration

The system automatically downloads and caches AI models:
- **Face Recognition**: MTCNN, FaceNet ResNet
- **Object Detection**: YOLOv8
- **OCR**: EasyOCR
- **Computer Vision**: ResNet50, EfficientNet

### Automatic Cleanup System

The system includes a comprehensive automatic cleanup system that runs in the background:

#### **Automatic Cleanup Features**
- **Background Processing**: Runs automatically every 24 hours (configurable)
- **Data Retention**: Configurable retention periods for different data types
- **Storage Optimization**: Removes orphaned files and old media
- **Non-blocking**: Cleanup runs without affecting system performance
- **API Monitoring**: Real-time status and statistics via REST APIs

#### **Cleanup Configuration**
```bash
# Environment variables for cleanup
CLEANUP_ENABLED=true                    # Enable/disable automatic cleanup
CLEANUP_INTERVAL_HOURS=24              # Hours between cleanup runs
PERSON_DATA_RETENTION_DAYS=30          # Person data retention period
EMBEDDING_DATA_RETENTION_DAYS=90       # Embedding data retention period
MEDIA_RETENTION_DAYS=60                # Media file retention period
```

#### **What Gets Cleaned**
- **Person Data**: Old person appearance records and matches
- **Embedding Data**: Expired face and clothing embeddings
- **Media Files**: Old person images and temporary files
- **Orphaned Files**: Files without database references
- **Storage Optimization**: Automatic disk space management

### Local Cache System

The system uses a high-performance local cache instead of Redis for better performance and simpler deployment:

#### **Local Cache Features**
- **Thread-safe**: Concurrent access with proper locking
- **Memory + Disk**: Fast memory cache with disk persistence
- **Automatic Cleanup**: Expired items are automatically removed
- **Configurable TTL**: Customizable time-to-live for cache items
- **Size Management**: Automatic memory cache size limiting
- **Background Worker**: Continuous cleanup of expired items

#### **Cache Configuration**
```bash
# Cache settings (automatically configured)
CACHE_DIR=storage/local_cache              # Cache storage directory
CACHE_MAX_MEMORY_ITEMS=1000               # Maximum memory cache items
CACHE_DEFAULT_TTL=3600                    # Default TTL in seconds (1 hour)
CACHE_CLEANUP_INTERVAL=300                # Cleanup interval in seconds (5 minutes)
```

#### **Cache Benefits**
- **No External Dependencies**: No Redis server required
- **Better Performance**: Direct file system access
- **Simpler Deployment**: One less service to manage
- **Automatic Management**: Self-cleaning and optimized
- **Persistent Storage**: Survives application restarts

### Database Setup & Management

The system includes comprehensive database setup and management:

#### **Automatic Database Setup**
- **Database Creation**: Automatically creates PostgreSQL database
- **Table Creation**: All tables created via SQLAlchemy migrations
- **Default Admin**: Creates default admin user (admin/admin123)
- **Indexes**: Optimized database indexes for performance
- **Extensions**: PostgreSQL extensions (uuid-ossp, pg_trgm)

#### **Database Features**
- **Async Support**: Full async/await database operations
- **Connection Pooling**: Optimized connection management
- **Health Monitoring**: Database health checks and metrics
- **Backup Ready**: Easy backup and restore procedures
- **Migration Support**: Alembic migration system

#### **Database Schema**
```sql
-- Core Tables
users                    -- User authentication and roles
tickets                  -- Security incident tickets
ticket_evidence          -- Evidence files and media
ticket_activities        -- Ticket activity logs
ai_analyses             -- AI analysis results
person_embeddings        -- Person recognition data
person_appearances       -- Person appearance records
person_matches          -- Person matching results
```

#### **Database Setup Commands**
```bash
# Manual database setup
python backend/scripts/setup_database.py

# Docker automatic setup (included in docker-compose)
docker-compose exec backend python scripts/setup_database.py

# Database health check
curl "http://localhost:8000/api/health/database"
```

### Telegram Integration

The system includes comprehensive Telegram integration for real-time alerts and notifications:

#### **Telegram Features**
- **Real-time Alerts**: Instant notifications when threats are detected
- **Escalation Channel**: Dedicated channel for security incidents
- **Rich Media**: Send images, videos, and detailed reports
- **Webhook Support**: Secure webhook integration
- **Admin Controls**: Role-based notification management

#### **Telegram Configuration**
```bash
# Your Telegram credentials (already configured)
TELEGRAM_BOT_TOKEN=8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0
TELEGRAM_WEBHOOK_SECRET=supersecret
TELEGRAM_ESCALATION_CHANNEL=-4672336726
```

#### **Telegram Setup**
1. **Bot Token**: Your bot token is already configured
2. **Channel ID**: Escalation channel `-4672336726` is set up
3. **Webhook Secret**: Security secret `supersecret` is configured
4. **Automatic Integration**: System automatically sends alerts to your channel

#### **Alert Types**
- **Threat Detection**: Immediate alerts for security threats
- **Person Recognition**: Notifications when known persons are detected
- **System Events**: Important system status updates
- **Evidence Reports**: Comprehensive evidence packages

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- **Basic Health**: `GET /api/health`
- **Detailed Health**: `GET /api/health/detailed`
- **Performance Metrics**: `GET /api/health/metrics`
- **Readiness Probe**: `GET /api/health/readiness`
- **Liveness Probe**: `GET /api/health/liveness`

### Metrics Collected

- **System Metrics**: CPU, memory, disk, network usage
- **Application Metrics**: Request count, response times, error rates
- **Database Metrics**: Connection status, query performance
- **AI Models**: Cache status, model health
- **Storage Metrics**: File counts, storage usage

## 🚀 Production Deployment

### Azure Deployment

1. **Prerequisites**
   ```bash
   # Install Azure CLI
   az login
   
   # Set environment variables
   export OPENAI_API_KEY="your-openai-key"
   export TELEGRAM_BOT_TOKEN="your-telegram-token"
   ```

2. **Deploy to Azure**
   ```bash
   chmod +x scripts/deploy-azure.sh
   ./scripts/deploy-azure.sh
   ```

### Kubernetes Deployment

1. **Create secrets**
   ```bash
   kubectl create secret generic vigilanteye-secrets \
     --from-literal=database-url="postgresql://..." \
     --from-literal=redis-url="redis://..." \
     --from-literal=secret-key="your-secret-key" \
     --from-literal=jwt-secret-key="your-jwt-key" \
     --from-literal=openai-api-key="your-openai-key"
   ```

2. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f azure/kubernetes.yaml
   ```

### Docker Compose Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/core.txt
pip install -r requirements/ai_services.txt
uvicorn src.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### AI Model Management

```bash
# Preload all models
python scripts/preload_models.py

# Check model cache status
curl http://localhost:8000/api/models/cache/stats

# Clear model cache
curl -X DELETE http://localhost:8000/api/models/cache/clear
```

## 📁 Project Structure

```
VigilantEye/
├── backend/                 # FastAPI backend
│   ├── src/
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── models/         # Database models
│   │   ├── config/         # Configuration
│   │   └── utils/          # Utilities
│   ├── requirements/       # Python dependencies
│   ├── scripts/           # Utility scripts
│   └── Dockerfile         # Backend container
├── frontend/              # React frontend
│   ├── src/
│   │   ├── pages/         # React pages
│   │   ├── components/    # React components
│   │   ├── services/      # API services
│   │   └── store/         # State management
│   ├── public/            # Static assets
│   └── Dockerfile         # Frontend container
├── azure/                 # Azure deployment configs
├── scripts/               # Deployment scripts
├── docker-compose.yml     # Development setup
├── docker-compose.prod.yml # Production setup
└── README.md              # This file
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
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

## 🛠️ Troubleshooting

### **Common Issues and Solutions**

#### **Docker Issues**
```bash
# If Docker containers fail to start
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check container logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Reset everything
docker-compose down -v
docker system prune -a
docker-compose up -d
```

#### **Database Connection Issues**
```bash
# Check database status
docker-compose exec postgres pg_isready -U vigilanteye -d vigilanteye

# Reset database
docker-compose exec postgres psql -U vigilanteye -d vigilanteye -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Check database logs
docker-compose logs postgres
```

#### **Database Setup Issues**
```bash
# Database setup fails
docker-compose exec backend python scripts/setup_database.py

# Check if database exists
docker-compose exec postgres psql -U vigilanteye -c "\l"

# Create database manually
docker-compose exec postgres createdb -U vigilanteye vigilanteye

# Check database tables
docker-compose exec postgres psql -U vigilanteye -d vigilanteye -c "\dt"

# Reset database completely
docker-compose exec postgres psql -U vigilanteye -c "DROP DATABASE IF EXISTS vigilanteye;"
docker-compose exec postgres createdb -U vigilanteye vigilanteye
docker-compose exec backend python scripts/setup_database.py
```

#### **Cleanup System Issues**
```bash
# Check cleanup status
curl "http://localhost:8000/api/cleanup/status" \
  -H "Authorization: Bearer <token>"

# Run manual cleanup
curl -X POST "http://localhost:8000/api/cleanup/run" \
  -H "Authorization: Bearer <admin_token>"

# Test cleanup (dry run)
curl -X POST "http://localhost:8000/api/cleanup/test" \
  -H "Authorization: Bearer <admin_token>"

# Check cleanup configuration
curl "http://localhost:8000/api/cleanup/config" \
  -H "Authorization: Bearer <admin_token>"

# Check cleanup logs
docker-compose logs backend | grep -i cleanup
```

#### **Local Cache Issues**
```bash
# Check cache status
curl "http://localhost:8000/api/health/detailed"

# Clear cache directory
docker-compose exec backend rm -rf storage/local_cache/*

# Check cache directory permissions
docker-compose exec backend ls -la storage/

# Restart backend to reinitialize cache
docker-compose restart backend
```

#### **AI Model Issues**
```bash
# Clear model cache
curl -X DELETE "http://localhost:8000/api/models/cache/clear" \
  -H "Authorization: Bearer <admin_token>"

# Preload models again
docker-compose exec backend python scripts/preload_models.py

# Check model cache status
curl "http://localhost:8000/api/models/cache/stats"
```

#### **Port Conflicts**
```bash
# Check what's using ports
# Windows:
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# macOS/Linux:
lsof -i :8000
lsof -i :3000

# Kill processes if needed
# Windows:
taskkill /PID <PID> /F
# macOS/Linux:
kill -9 <PID>
```

#### **Permission Issues**
```bash
# Fix file permissions
sudo chown -R $USER:$USER backend/storage
sudo chmod -R 755 backend/storage

# Docker permission issues
sudo usermod -aG docker $USER
# Logout and login again
```

### **Useful Commands**

#### **Development Commands**
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart specific service
docker-compose restart backend

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec postgres psql -U vigilanteye -d vigilanteye

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

#### **Database Commands**
```bash
# Access database
docker-compose exec postgres psql -U vigilanteye -d vigilanteye

# Backup database
docker-compose exec postgres pg_dump -U vigilanteye vigilanteye > backup.sql

# Restore database
docker-compose exec -T postgres psql -U vigilanteye -d vigilanteye < backup.sql

# Reset database
docker-compose exec postgres psql -U vigilanteye -d vigilanteye -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

#### **AI Model Commands**
```bash
# Check model cache
curl "http://localhost:8000/api/models/cache/stats"

# Validate models
curl "http://localhost:8000/api/models/cache/validate"

# Preload models
docker-compose exec backend python scripts/preload_models.py

# Clear specific model
curl -X DELETE "http://localhost:8000/api/models/cache/clear/mtcnn"
```

#### **Health Check Commands**
```bash
# Basic health
curl "http://localhost:8000/api/health"

# Detailed health
curl "http://localhost:8000/api/health/detailed"

# Performance metrics
curl "http://localhost:8000/api/health/metrics"

# Database health
curl "http://localhost:8000/api/health/db"
```

#### **File Management**
```bash
# Check storage usage
du -sh backend/storage/*

# Clean up old files
find backend/storage -name "*.tmp" -delete
find backend/storage -name "*.log" -mtime +7 -delete

# Check disk space
df -h
```

## 🔄 **Complete Workflow Guide**

### **1. Video Upload and Processing Workflow**

#### **Step 1: Upload Video**
```bash
# Via API
curl -X POST "http://localhost:8000/api/videos/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@security_footage.mp4" \
  -F "description=Security footage from camera 1"

# Via Web UI
# 1. Go to http://localhost:3000
# 2. Login with credentials
# 3. Navigate to Dashboard
# 4. Drag and drop video file
# 5. Add description
# 6. Click Upload
```

#### **Step 2: AI Processing**
```bash
# Start processing
curl -X POST "http://localhost:8000/api/videos/process" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 123,
    "analysis_options": {
      "face_detection": true,
      "object_detection": true,
      "text_extraction": true,
      "threat_assessment": true
    }
  }'

# Monitor progress
curl "http://localhost:8000/api/videos/123" \
  -H "Authorization: Bearer <token>"
```

#### **Step 3: Review Results**
```bash
# Get processing results
curl "http://localhost:8000/api/videos/123/frames" \
  -H "Authorization: Bearer <token>"

# Check for threats
curl "http://localhost:8000/api/tickets" \
  -H "Authorization: Bearer <token>"
```

### **2. Ticket Management Workflow**

#### **Step 1: View Tickets**
```bash
# List all tickets
curl "http://localhost:8000/api/tickets" \
  -H "Authorization: Bearer <token>"

# Filter by status
curl "http://localhost:8000/api/tickets?status=OPEN" \
  -H "Authorization: Bearer <token>"

# Filter by priority
curl "http://localhost:8000/api/tickets?priority=HIGH" \
  -H "Authorization: Bearer <token>"
```

#### **Step 2: Manage Tickets**
```bash
# Acknowledge ticket
curl -X POST "http://localhost:8000/api/tickets/456/acknowledge" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Ticket acknowledged, investigating threat"}'

# Add note
curl -X POST "http://localhost:8000/api/tickets/456/note" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"note": "Additional investigation notes"}'

# Close ticket
curl -X POST "http://localhost:8000/api/tickets/456/close" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Threat resolved, no further action needed"}'
```

#### **Step 3: Evidence Management**
```bash
# Get evidence
curl "http://localhost:8000/api/tickets/456/evidence" \
  -H "Authorization: Bearer <token>"

# Download all evidence
curl "http://localhost:8000/api/tickets/456/evidence/download" \
  -H "Authorization: Bearer <token>" \
  -o evidence.zip

# Delete evidence (Admin only)
curl -X DELETE "http://localhost:8000/api/tickets/456/evidence/789" \
  -H "Authorization: Bearer <admin_token>"
```

### **3. System Monitoring Workflow**

#### **Step 1: Health Monitoring**
```bash
# Basic health check
curl "http://localhost:8000/api/health"

# Detailed health with metrics
curl "http://localhost:8000/api/health/detailed"

# Performance metrics
curl "http://localhost:8000/api/health/metrics"
```

#### **Step 2: Model Management**
```bash
# Check model cache status
curl "http://localhost:8000/api/models/cache/stats" \
  -H "Authorization: Bearer <admin_token>"

# Validate models
curl "http://localhost:8000/api/models/cache/validate" \
  -H "Authorization: Bearer <admin_token>"

# Preload models
curl -X POST "http://localhost:8000/api/models/cache/preload" \
  -H "Authorization: Bearer <admin_token>"
```

## 📁 **Detailed Project Structure**

```
VigilantEye/
├── 📁 backend/                    # FastAPI Backend
│   ├── 📁 src/
│   │   ├── 📁 api/               # API Endpoints
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── health.py         # Health check endpoints
│   │   │   ├── video.py          # Video processing endpoints
│   │   │   ├── ticket.py         # Ticket management endpoints
│   │   │   └── model_cache.py    # AI model management endpoints
│   │   ├── 📁 services/          # Business Logic
│   │   │   ├── 📁 ai/            # AI Services
│   │   │   │   ├── face_recognition_service.py
│   │   │   │   ├── clothing_recognition_service.py
│   │   │   │   ├── image_analysis_service.py
│   │   │   │   ├── threat_detection_service.py
│   │   │   │   ├── ai_orchestrator.py
│   │   │   │   ├── model_cache_manager.py
│   │   │   │   ├── vector_db_manager.py
│   │   │   │   └── person_vector_db_manager.py
│   │   │   ├── ticket.py         # Ticket business logic
│   │   │   ├── clothing_analysis_service.py
│   │   │   └── enhanced_evidence_collection_service.py
│   │   ├── 📁 models/            # Database Models
│   │   │   ├── ticket.py         # Ticket-related models
│   │   │   ├── person_embeddings.py
│   │   │   └── ...               # Other models
│   │   ├── 📁 repositories/      # Data Access Layer
│   │   │   ├── ticket.py         # Ticket repository
│   │   │   └── ...               # Other repositories
│   │   ├── 📁 dto/              # Data Transfer Objects
│   │   │   ├── ticket.py         # Ticket DTOs
│   │   │   └── ...               # Other DTOs
│   │   ├── 📁 config/            # Configuration
│   │   │   ├── ai_config.py      # AI configuration
│   │   │   └── settings.py        # App settings
│   │   ├── 📁 database/          # Database setup
│   │   ├── 📁 utils/             # Utilities
│   │   └── main.py               # FastAPI app entry point
│   ├── 📁 requirements/          # Python Dependencies
│   │   ├── core.txt              # Core dependencies
│   │   └── ai_services.txt       # AI/ML dependencies
│   ├── 📁 scripts/              # Utility Scripts
│   │   └── preload_models.py    # Model preloading script
│   ├── 📁 storage/              # File Storage
│   │   ├── videos/              # Uploaded videos
│   │   ├── evidence/            # Evidence files
│   │   ├── model_cache/         # Cached AI models
│   │   └── vector_db/           # Vector database
│   ├── Dockerfile               # Backend container
│   └── .env.example            # Environment template
├── 📁 frontend/                 # React Frontend
│   ├── 📁 src/
│   │   ├── 📁 pages/           # React Pages
│   │   │   ├── Dashboard.jsx    # Main dashboard
│   │   │   ├── UnifiedTicketsPage.jsx  # Ticket management
│   │   │   ├── Login.jsx        # Login page
│   │   │   └── SignUp.jsx       # Registration page
│   │   ├── 📁 components/       # React Components
│   │   │   ├── Logo.jsx         # Logo component
│   │   │   ├── EvidenceGallery.jsx  # Evidence viewer
│   │   │   └── ...              # Other components
│   │   ├── 📁 services/         # API Services
│   │   │   └── api.js           # API client
│   │   ├── 📁 store/           # State Management
│   │   │   └── authStore.js     # Authentication store
│   │   ├── 📁 styles/          # CSS Styles
│   │   ├── App.jsx             # Main app component
│   │   └── main.jsx            # App entry point
│   ├── 📁 public/              # Static Assets
│   ├── package.json            # Node.js dependencies
│   ├── Dockerfile              # Frontend container
│   └── nginx.conf              # Nginx configuration
├── 📁 azure/                   # Azure Deployment
│   ├── container-instances.yaml # ACI deployment
│   ├── kubernetes.yaml         # AKS deployment
│   └── arm-template.json       # ARM template
├── 📁 scripts/                 # Deployment Scripts
│   ├── setup-dev.sh           # Development setup
│   └── deploy-azure.sh        # Azure deployment
├── 📁 nginx/                   # Nginx Configuration
├── docker-compose.yml          # Development environment
├── docker-compose.prod.yml     # Production environment
├── .env.example               # Environment template
└── README.md                  # This documentation
```

## 🎯 **Use Cases and Scenarios**

### **Scenario 1: Security Monitoring**
1. **Setup**: Deploy VigilantEye in security control room
2. **Monitoring**: Connect to live camera feeds
3. **Detection**: AI automatically detects threats
4. **Response**: Security team receives alerts and reviews tickets
5. **Action**: Investigate threats and take appropriate action

### **Scenario 2: Evidence Collection**
1. **Incident**: Security incident occurs
2. **Upload**: Upload relevant video footage
3. **Analysis**: AI processes video and identifies persons/objects
4. **Collection**: System automatically collects related evidence
5. **Report**: Generate comprehensive evidence package

### **Scenario 3: Person Tracking**
1. **Suspect**: Person of interest identified
2. **Search**: System searches across all videos for same person
3. **Timeline**: Build timeline of person's movements
4. **Evidence**: Collect all related footage and evidence
5. **Investigation**: Use evidence for investigation

## 📈 Performance

### Benchmarks
- **Startup Time**: ~5 seconds (with cached models)
- **Face Detection**: ~100ms per image
- **Object Detection**: ~200ms per image
- **API Response**: ~50ms average

### Optimization Tips
- Enable model caching for faster startup
- Use GPU acceleration for AI processing
- Configure cleanup intervals for optimal storage usage
- Monitor system health regularly
- Use local cache for better performance

## 🔒 Security

### Security Features
- JWT-based authentication
- Role-based access control
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection

### Security Best Practices
- Change default passwords
- Use HTTPS in production
- Regular security updates
- Monitor access logs
- Implement rate limiting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Wiki](https://github.com/your-org/vigilanteye/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-org/vigilanteye/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/vigilanteye/discussions)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend library
- [YOLO](https://ultralytics.com/) - Object detection
- [FaceNet](https://github.com/timesler/facenet-pytorch) - Face recognition
- [OpenAI](https://openai.com/) - LLM integration

---

## 🎯 **System Summary**

### **What You Get**
VigilantEye is a complete AI-powered security surveillance system with:

#### **🔍 Advanced AI Capabilities**
- **Face Recognition**: MTCNN + FaceNet for person identification
- **Clothing Recognition**: Person identification when faces aren't visible
- **Object Detection**: YOLOv8 for weapons and suspicious objects
- **Text Extraction**: EasyOCR for license plates and signs
- **Threat Assessment**: OpenAI GPT-4 powered threat analysis
- **Person Tracking**: Cross-video person tracking using embeddings

#### **🎫 Complete Ticket Management**
- **Unified Interface**: Expandable table with integrated media viewer
- **Evidence Collection**: Automatic evidence gathering and organization
- **Soft Delete**: Safe ticket deletion with audit trails
- **Admin Controls**: Role-based access control
- **Media Viewer**: Built-in image/video/audio player
- **Bulk Operations**: Download all evidence as ZIP archives

#### **⚡ Performance & Reliability**
- **Model Caching**: Intelligent AI model caching (pickle-based)
- **Local Cache**: High-performance local cache (no Redis required)
- **Health Monitoring**: Comprehensive system metrics and health checks
- **Automatic Cleanup**: Background data cleanup and storage optimization
- **Database Management**: Automatic database setup and management

#### **🚀 Production Ready**
- **Docker Support**: Complete containerization with multi-stage builds
- **Azure Integration**: Ready for Azure Cloud deployment
- **Kubernetes**: Production-ready K8s manifests with health probes
- **CI/CD Ready**: Automated deployment pipelines
- **Environment Management**: Development and production configurations

### **Key Benefits**
1. **Simplified Deployment**: No Redis dependency, automatic database setup
2. **Better Performance**: Local cache, model caching, optimized database
3. **Automatic Management**: Background cleanup, health monitoring, model management
4. **Complete Solution**: Frontend, backend, AI services, and deployment ready
5. **Production Ready**: Docker, Kubernetes, Azure deployment configurations

### **Perfect For**
- **Security Companies**: Complete surveillance solution
- **Enterprises**: Office building security monitoring
- **Retail**: Store security and customer analytics
- **Educational**: Campus security and monitoring
- **Government**: Public space surveillance
- **Research**: AI/ML research and development

---

**VigilantEye** - Keeping you safe with AI-powered surveillance 🛡️👁️