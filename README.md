# 🚀 VIGILANTEye - Video Surveillance Management System

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/AIP-F25-2/VigilantEye)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A comprehensive video surveillance management system with Telegram integration, built with Flask and deployed on Azure.

**Repository**: [https://github.com/AIP-F25-2/VigilantEye](https://github.com/AIP-F25-2/VigilantEye)

## 🌟 Features

### Core Functionality
- **Video Management**: Upload, process, and manage surveillance videos
- **User Authentication**: Secure login/registration with JWT tokens
- **Project Management**: Organize surveillance projects and recordings
- **Analytics**: View events and analytics data
- **Device Management**: Manage surveillance devices

### Telegram Integration
- **Message Ingestion**: Send alerts and notifications via Telegram
- **Webhook Support**: Handle Telegram callbacks and acknowledgments
- **Auto-escalation**: Automatic message escalation after timeout
- **Background Jobs**: Scheduled message processing and cleanup

### Technical Features
- **REST API**: Complete RESTful API with proper error handling
- **Database**: MySQL with SQLAlchemy ORM and migrations
- **Security**: JWT authentication, HTTPS, SSL database connections
- **Deployment**: Azure Container Apps with auto-scaling
- **Monitoring**: Health checks and comprehensive logging

## 🏗️ Architecture

```
VIGILANTEye/
├── app/
│   ├── controllers/          # API and web controllers
│   ├── models/              # Database models
│   ├── schemas/             # Marshmallow schemas
│   ├── services/            # Business logic services
│   ├── templates/           # HTML templates
│   └── utils/               # Utility functions
├── migrations/              # Database migrations
├── config.py               # Configuration
├── run.py                  # Application entry point
└── requirements.txt        # Dependencies
```

## 🚀 Quick Start

### Local Development

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/AIP-F25-2/VigilantEye.git
   cd VigilantEye
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/vigilanteye"
   flask db upgrade
   ```

3. **Run Application**:
   ```bash
   python run.py
   ```

### Docker Development

1. **Start Services**:
   ```bash
   docker-compose up -d
   ```

2. **Access Application**:
   - Web: http://localhost:8000
   - API: http://localhost:8000/api/v1/
   - Health: http://localhost:8000/health

## 🌐 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Core API
- `GET /api/v1/users` - List users
- `GET /api/v1/videos` - List videos
- `GET /api/v1/projects` - List projects
- `GET /api/v1/recordings` - List recordings

### Telegram Integration
- `POST /api/telegram/ingest` - Send message to Telegram
- `POST /webhook/telegram/<secret>` - Telegram webhook

### Web Interface
- `GET /` - Homepage
- `GET /login` - Login page
- `GET /register` - Registration page
- `GET /dashboard` - User dashboard

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=mysql+pymysql://user:pass@host:3306/database?ssl_ca=/path/to/ca.pem

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# Message Processing
ESCALATE_AFTER_SECONDS=900
CLOSE_AFTER_SECONDS=3600
```

### Telegram Setup

1. **Create Bot**: Message @BotFather on Telegram
2. **Get Token**: Save the bot token
3. **Configure Webhook**: Set webhook URL to your domain
4. **Test Integration**: Use the ingest API endpoint

## 🚀 Azure Deployment

### Prerequisites
- Azure CLI installed
- Docker installed
- Azure Container Registry

### Deploy Steps

1. **Build and Push**:
   ```bash
   docker build -t vigilanteye:latest .
   az acr login --name your-registry
   docker tag vigilanteye:latest your-registry.azurecr.io/vigilanteye:latest
   docker push your-registry.azurecr.io/vigilanteye:latest
   ```

2. **Create Container App**:
   ```bash
   az containerapp create \
     --name vigilanteye-app \
     --resource-group your-rg \
     --environment your-env \
     --image your-registry.azurecr.io/vigilanteye:latest
   ```

3. **Configure Environment**:
   ```bash
   az containerapp update \
     --name vigilanteye-app \
     --resource-group your-rg \
     --set-env-vars "DATABASE_URL=your-db-url" "TELEGRAM_BOT_TOKEN=your-token"
   ```

## 📊 Database Schema

### Core Tables
- `users` - User accounts and authentication
- `projects` - Surveillance projects
- `videos` - Video files and metadata
- `recordings` - Recording sessions
- `devices` - Surveillance devices
- `analytics` - Analytics data

### Telegram Integration
- `outbound_messages` - Telegram messages and status

## 🧪 Testing

### API Testing
```bash
# Health check
curl https://your-app.azurecontainerapps.io/health

# Telegram message
curl -X POST https://your-app.azurecontainerapps.io/api/telegram/ingest \
  -H "Content-Type: application/json" \
  -d '{"type":"text","content":"Test message","channel_id":"-123456789"}'
```

### Web Interface
- Visit https://your-app.azurecontainerapps.io/
- Test login/registration
- Access dashboard features

## 📈 Monitoring

### Health Checks
- Application health: `/health`
- Database connectivity: Automatic
- Telegram bot status: Via API

### Logs
- Azure Container Apps logs
- Application logs via Python logging
- Database query logs

## 🔒 Security

- **HTTPS**: SSL/TLS encryption
- **JWT**: Secure token-based authentication
- **Database SSL**: Encrypted database connections
- **Input Validation**: Marshmallow schema validation
- **CORS**: Configured cross-origin resource sharing

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository: [https://github.com/AIP-F25-2/VigilantEye](https://github.com/AIP-F25-2/VigilantEye)
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contributors

- [@Sukhjitsingh2](https://github.com/Sukhjitsingh2) - sukhjit singh
- [@NSriDatta16](https://github.com/NSriDatta16) - N SriDatta
- [@probablybhavik](https://github.com/probablybhavik) - Bhavik Gandhi
- [@sameerkeshvani](https://github.com/sameerkeshvani)

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the documentation
- Review the API endpoints
- Check Azure Container Apps logs
- Test individual components

---

**VIGILANTEye** - Professional video surveillance management with modern web technologies and Telegram integration.