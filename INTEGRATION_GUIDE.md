# VIGILANTEye Integration Guide

## 📁 Project Structure

```
VigilantEye-Integrated/
├── app/                       # Advanced Flask application structure
│   ├── controllers/           # API and web controllers
│   │   ├── api.py            # REST API endpoints
│   │   ├── auth_controller.py # Authentication handling
│   │   ├── telegram_controller.py # Telegram integration
│   │   └── web_auth_controller.py # Web authentication
│   ├── models/               # Database models (SQLAlchemy)
│   │   ├── user.py           # User management
│   │   ├── video.py          # Video management
│   │   ├── project.py        # Project management
│   │   └── outbound_message.py # Telegram messages
│   ├── schemas/              # Marshmallow serialization schemas
│   ├── services/             # Business logic services
│   │   ├── telegram_client.py # Telegram bot integration
│   │   └── scheduler.py      # Background job scheduler
│   ├── templates/            # HTML templates
│   │   ├── auth/             # Authentication pages
│   │   ├── dashboard.html    # Main dashboard
│   │   └── base.html         # Base template
│   ├── static/               # CSS/JS assets
│   └── utils/                # Utility functions
├── migrations/               # Database migrations (Alembic)
├── config.py                # Application configuration
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Local development setup
├── deploy-azure.ps1        # Azure deployment script
└── README.md               # Comprehensive documentation
```

## ✨ What's Integrated

### Advanced Production Features:
- ✅ **Professional Architecture**: Modular Flask app with controllers, models, schemas
- ✅ **Database Integration**: SQLAlchemy ORM with MySQL and migrations
- ✅ **Authentication System**: JWT-based API authentication + session-based web auth
- ✅ **REST API**: Complete RESTful API with proper error handling
- ✅ **Telegram Integration**: Full bot functionality with webhooks and auto-escalation
- ✅ **Background Jobs**: APScheduler for message processing and cleanup
- ✅ **Security**: HTTPS, SSL database connections, CORS configuration
- ✅ **Deployment Ready**: Docker, Azure Container Apps, auto-scaling

### Core Functionality:
- ✅ **User Management**: Registration, login, profile management
- ✅ **Project Management**: Organize surveillance projects and recordings
- ✅ **Video Management**: Upload, process, and manage surveillance videos
- ✅ **Analytics**: View events and analytics data
- ✅ **Device Management**: Manage surveillance devices
- ✅ **Message Processing**: Telegram message ingestion and status tracking

## 🚀 How to Use

### Option 1: Local Development (Recommended)
1. **Install dependencies:**
   ```bash
   cd VigilantEye-Integrated
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Create .env file with:
   DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/vigilanteye
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_WEBHOOK_SECRET=your-webhook-secret
   ```

3. **Initialize database:**
   ```bash
   flask db upgrade
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

5. **Access the application:**
   - Web Interface: `http://localhost:8000`
   - API: `http://localhost:8000/api/v1/`
   - Health Check: `http://localhost:8000/health`

### Option 2: Docker Development
1. **Start with Docker Compose:**
   ```bash
   cd VigilantEye-Integrated
   docker-compose up -d
   ```

2. **Access the application:**
   - Web: `http://localhost:8000`
   - API: `http://localhost:8000/api/v1/`

### Option 3: Azure Deployment
1. **Deploy to Azure:**
   ```bash
   cd VigilantEye-Integrated
   .\deploy-azure.ps1
   ```

2. **Configure environment variables in Azure Container Apps**
3. **Access your deployed application via Azure URL**

## 🔧 Key Improvements Made

1. **Production-Ready Architecture**: Professional Flask app structure with proper separation of concerns
2. **Database Integration**: SQLAlchemy ORM with migrations for robust data management
3. **Authentication System**: Dual authentication (JWT for API, sessions for web)
4. **Telegram Integration**: Complete bot functionality with webhooks and message tracking
5. **API-First Design**: RESTful API with comprehensive endpoints
6. **Deployment Ready**: Docker, Azure Container Apps, and auto-scaling support

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

## 🔒 Security Features

- **HTTPS**: SSL/TLS encryption
- **JWT Authentication**: Secure token-based API authentication
- **Database SSL**: Encrypted database connections
- **Input Validation**: Marshmallow schema validation
- **CORS**: Configured cross-origin resource sharing

## 🚀 Next Steps

1. **Set up your database** (MySQL) and configure environment variables
2. **Test the API endpoints** using the provided documentation
3. **Configure Telegram bot** by getting a bot token from @BotFather
4. **Deploy to Azure** using the provided deployment script
5. **Customize the application** for your specific surveillance needs

## 🎉 Success!

The advanced VigilantEye-dev version has been successfully integrated! You now have:
- A production-ready Flask application with professional architecture
- Complete database integration with SQLAlchemy and migrations
- Full Telegram bot integration with webhooks and message tracking
- RESTful API with comprehensive endpoints
- Docker and Azure deployment support
- Comprehensive documentation and setup guides

This is a significant upgrade from the basic version, providing enterprise-level features and scalability for your video surveillance management system!
