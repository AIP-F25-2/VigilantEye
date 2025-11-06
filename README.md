# VIGILANTEye - Multi-Agent Video Intelligence Platform

A next-generation, AI-powered, multi-agent security platform that combines anomaly detection, action recognition, face and vehicle identification, and human-in-the-loop feedback to deliver explainable, proactive, and scalable video intelligence.

## 🚀 Features

### Core Video Intelligence
- **Face & Identity Agent**: Face detection, recognition, and re-identification across multiple cameras
- **Watchlist Integration**: Employees, VIPs, suspects management
- **Cross-age and Disguise Detection**: Masks, hats, glasses detection
- **Demographics Estimation**: Age band, gender estimation for analytics (privacy configurable)

### Application Features
- User authentication and authorization
- Real-time CCTV video processing
- Face detection and recognition
- Person tracking across cameras
- Watchlist alerts
- Telegram integration for notifications
- Web dashboards for monitoring

## 📋 Prerequisites

- Python 3.11+
- MySQL Database
- Azure Account (for deployment)
- Docker (for containerization)

## 🛠️ Installation

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (see `.env.example`)
4. Run database migrations:
   ```bash
   flask db upgrade
   ```
5. Start the application:
   ```bash
   python run.py
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## 📦 Azure Deployment

### Quick Deployment

```powershell
.\deploy-azure.ps1
```

### Manual Deployment

See `MANUAL_DEPLOYMENT_STEPS.md` for detailed instructions.

## 🔧 Configuration

Key environment variables:
- `DATABASE_URL`: MySQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_WEBHOOK_SECRET`: Webhook secret

## 📚 API Endpoints

### Health Check
- `GET /health` - Application health status

### FaceAi API
- `GET /api/faceai/status` - FaceAi service status
- `POST /api/faceai/detect` - Face detection
- `POST /api/faceai/demographics` - Demographics analysis
- `POST /api/faceai/ambiguity` - Ambiguity detection

### CCTV API
- `GET /api/cctv/status` - Agent status
- `POST /api/cctv/process` - Process CCTV video
- `GET /api/cctv/watchlist` - Get watchlist
- `POST /api/cctv/watchlist` - Add to watchlist

### Telegram API
- `POST /api/telegram/ingest` - Ingest messages
- `POST /webhook/telegram/<secret>` - Webhook handler

## 🎯 User Personas

- Corporate Security Managers
- Retail Security Leads
- Event & Venue Organizers
- Educational Institutions
- Transport Hub Authorities
- Government & Smart City Operators
- Healthcare Facility Admins

## 📖 Documentation

- `FACEAI_INTEGRATION_GUIDE.md` - FaceAi integration details
- `FACE_IDENTITY_AGENT_GUIDE.md` - CCTV agent documentation
- `AZURE_DEPLOYMENT_FACEAI_GUIDE.md` - Azure deployment guide
- `MIGRATION_SOLUTION.md` - Database migration guide
- `DEPLOYMENT_SUMMARY.md` - Deployment status

## 🏗️ Project Structure

```
VIGILANTEye/
├── app/
│   ├── controllers/      # API and web controllers
│   ├── models/           # Database models
│   ├── services/         # Business logic services
│   ├── templates/       # HTML templates
│   └── static/          # CSS, JS, images
├── migrations/          # Database migrations
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── run.py              # Application entry point
```

## 🔒 Security

- JWT-based API authentication
- Session-based web authentication
- Password hashing with bcrypt
- HTTPS enabled on Azure deployment

## 📝 License

[Your License Here]

## 🤝 Contributing

[Contributing Guidelines]

## 📧 Support

For issues and questions, please open an issue on GitHub.
