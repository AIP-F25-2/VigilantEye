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

## 🔧 Configuration

### Environment Variables

```env
# Database Configuration
POSTGRES_DB=vigilanteye
POSTGRES_USER=vigilanteye
POSTGRES_PASSWORD=vigilanteye123

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
# Development
docker-compose up -d                    # Start all services
docker-compose logs -f                  # View logs
docker-compose restart backend          # Restart backend
docker-compose exec backend bash        # Access backend container

# Database
docker-compose exec postgres psql -U vigilanteye -d vigilanteye
docker-compose exec backend python scripts/setup_database.py

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