# VigilantEye - AI-Powered Security Surveillance System

## 🎯 Overview

VigilantEye is a comprehensive AI-powered security surveillance system that provides real-time threat detection, person recognition, and evidence collection. The system combines computer vision, machine learning, and modern web technologies to deliver a complete security solution.

## ✨ Key Features

### 🔍 **AI-Powered Analysis**
- **Face Recognition**: Detect and identify individuals using advanced face recognition
- **Clothing Recognition**: Identify people based on clothing and appearance when faces aren't visible
- **Object Detection**: Detect weapons, suspicious objects, and activities using YOLO
- **Text Recognition**: Extract text from images using OCR
- **Threat Assessment**: AI-powered threat analysis using LLM integration

### 📊 **Performance & Monitoring**
- **Real-time Metrics**: Comprehensive performance monitoring
- **Health Checks**: Kubernetes-ready health probes
- **Model Caching**: Intelligent AI model caching for faster startup
- **System Metrics**: CPU, memory, disk, and network monitoring

### 🎫 **Ticket Management**
- **Unified Interface**: Expandable table with integrated media viewer
- **Evidence Collection**: Automatic evidence gathering and organization
- **Soft Delete**: Safe ticket deletion with audit trails
- **Admin Controls**: Role-based access control

### 🚀 **Deployment Ready**
- **Docker Support**: Complete containerization
- **Azure Integration**: Ready for Azure Cloud deployment
- **Kubernetes**: Production-ready K8s manifests
- **CI/CD Ready**: Automated deployment pipelines

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
                       │   Redis Cache   │
                       │   & Sessions    │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for development)
- Python 3.11+ (for development)

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

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://vigilanteye:vigilanteye123@postgres:5432/vigilanteye` |
| `REDIS_URL` | Redis connection string | `redis://:vigilanteye123@redis:6379/0` |
| `SECRET_KEY` | Application secret key | `your-secret-key-change-in-production` |
| `JWT_SECRET_KEY` | JWT signing key | `your-jwt-secret-key-change-in-production` |
| `OPENAI_API_KEY` | OpenAI API key for LLM | - |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - |
| `AI_DEVICE` | AI processing device | `cpu` |
| `MODEL_CACHE_ENABLED` | Enable model caching | `true` |

### AI Model Configuration

The system automatically downloads and caches AI models:
- **Face Recognition**: MTCNN, FaceNet ResNet
- **Object Detection**: YOLOv8
- **OCR**: EasyOCR
- **Computer Vision**: ResNet50, EfficientNet

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

## 📈 Performance

### Benchmarks
- **Startup Time**: ~5 seconds (with cached models)
- **Face Detection**: ~100ms per image
- **Object Detection**: ~200ms per image
- **API Response**: ~50ms average

### Optimization Tips
- Enable model caching for faster startup
- Use GPU acceleration for AI processing
- Configure Redis for session storage
- Use CDN for static assets

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

**VigilantEye** - Keeping you safe with AI-powered surveillance 🛡️👁️