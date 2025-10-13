# VIGILANTEye - AI-Powered Video Surveillance System

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/VigilantEye/actions/workflows/main.yml/badge.svg)](https://github.com/YOUR_USERNAME/VigilantEye/actions/workflows/main.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

VIGILANTEye is an advanced video surveillance and management system with AI-powered real-time monitoring, automated alerts, and comprehensive analytics.

## ✨ Features

- 🎥 **Live Video Monitoring** - Real-time surveillance feed management
- 🤖 **AI Detection** - Motion, intrusion, PPE compliance detection
- 📊 **Analytics Dashboard** - Comprehensive insights and reporting
- 🔔 **Smart Alerts** - Automated notifications (Email/Slack/Webhooks)
- 🔒 **Secure** - JWT & session-based authentication, HTTPS enabled
- 🚀 **Auto-scaling** - Handles traffic spikes automatically
- 📱 **Responsive** - Works on desktop, tablet, and mobile

## 🌐 Live Demo

**Production URL**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io

## 🏗️ Tech Stack

### Backend
- **Framework**: Flask 3.0+
- **Database**: MySQL 8.0 (Azure Database for MySQL)
- **ORM**: SQLAlchemy with Alembic migrations
- **Authentication**: Flask-JWT-Extended + Session-based
- **API**: RESTful with Marshmallow validation

### Frontend
- **Templates**: Jinja2
- **CSS**: Bootstrap 5.1.3
- **Icons**: Bootstrap Icons
- **JavaScript**: Vanilla JS

### DevOps
- **CI/CD**: GitHub Actions
- **Orchestration**: Apache Airflow
- **Containers**: Docker
- **Registry**: Azure Container Registry
- **Hosting**: Azure Container Apps (with HTTPS)
- **Monitoring**: Azure Application Insights

## 🚀 Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/VigilantEye.git
cd VigilantEye

# Start all services
docker-compose up -d

# Access the application
open http://localhost:8000
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/flaskapi"
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="jwt-secret"

# Run migrations
flask db upgrade

# Start application
python run.py
```

### Option 3: Start with Airflow

```bash
# Start Airflow for workflow orchestration
.\start-airflow.ps1  # Windows
# or
./start-airflow.sh   # Linux/Mac

# Access Airflow UI
open http://localhost:8080
# Username: admin
# Password: admin123
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [CICD_AIRFLOW_GUIDE.md](CICD_AIRFLOW_GUIDE.md) | Complete CI/CD & Airflow setup |
| [GITHUB_SETUP.md](GITHUB_SETUP.md) | GitHub configuration guide |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Azure deployment instructions |
| [HTTPS_SETUP.md](HTTPS_SETUP.md) | HTTPS configuration options |
| [ROUTES_STRUCTURE.md](ROUTES_STRUCTURE.md) | API & web routes documentation |
| [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) | Frontend details |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Project organization |
| [QUICKSTART.md](QUICKSTART.md) | Quick start guide |

## 📁 Project Structure

```
VigilantEye/
├── .github/workflows/        # CI/CD pipelines
├── app/                      # Main application
│   ├── controllers/         # Route handlers
│   ├── models/              # Database models
│   ├── schemas/             # Validation schemas
│   ├── templates/           # HTML templates
│   ├── static/              # CSS, JS, images
│   └── utils/               # Helper functions
├── airflow/                  # Airflow DAGs
│   ├── dags/                # Workflow definitions
│   ├── logs/                # Airflow logs
│   └── plugins/             # Custom operators
├── migrations/               # Database migrations
├── tests/                    # Unit tests
├── docker-compose.yml        # Local development
├── docker-compose.airflow.yml # Airflow setup
└── Dockerfile                # Container definition
```

## 🔑 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

### Videos
- `GET /api/v2/videos` - List videos
- `POST /api/v2/videos` - Create video
- `GET /api/v2/videos/{id}` - Get video details
- `PUT /api/v2/videos/{id}` - Update video
- `DELETE /api/v2/videos/{id}` - Delete video

### Projects
- `GET /api/v2/projects` - List projects
- `POST /api/v2/projects` - Create project
- `GET /api/v2/projects/{id}` - Get project

### Recordings
- `GET /api/v2/recordings` - List recordings
- `POST /api/v2/recordings` - Create recording

## 🎨 Web Pages

- `/` - Landing page
- `/login` - User login
- `/register` - User registration
- `/dashboard` - Monitoring dashboard (requires auth)
- `/profile` - User profile (requires auth)

## 🔄 CI/CD Pipeline

### Automated Workflows

1. **Pull Request Checks**
   - Code linting and formatting
   - Security vulnerability scanning
   - Unit tests with coverage

2. **Staging Deployment** (on push to `develop`)
   - Build and push Docker image
   - Deploy to staging environment
   - Run integration tests

3. **Production Deployment** (on push to `main`)
   - Run full test suite
   - Build optimized Docker image
   - Deploy to production (zero-downtime)
   - Run database migrations
   - Trigger Airflow workflows

## 🌊 Apache Airflow Workflows

### Available DAGs

1. **Video Processing Pipeline** - Hourly
   - Fetch and process pending videos
   - Generate thumbnails
   - Update analytics

2. **Analytics Pipeline** - Daily at 2 AM
   - Extract metrics
   - Calculate trends
   - Generate insights
   - Send daily report

3. **Database Maintenance** - Daily at 3 AM
   - Cleanup old recordings
   - Archive old videos
   - Optimize database tables

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 📦 Deployment

### Deploy to Production

```bash
# Option 1: Via GitHub (Automated)
git push origin main
# CI/CD pipeline handles everything

# Option 2: Manual Deployment
.\deploy.ps1  # Windows
./deploy.sh   # Linux/Mac
```

### Start Airflow

```bash
.\start-airflow.ps1  # Windows
./start-airflow.sh   # Linux/Mac
```

## 🔧 Configuration

### Environment Variables

```bash
FLASK_ENV=production
SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<jwt-secret>
DATABASE_URL=<mysql-connection-string>
```

### Airflow Configuration

Edit `airflow/dags/*.py` to customize workflows.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- Flask team for the excellent framework
- Apache Airflow community
- Azure Container Apps team
- Bootstrap team for UI components

## 📞 Support

For issues, please open a GitHub issue or contact: admin@vigilanteye.com

---

**Built with ❤️ for better security and safety**