# VIGILANTEye Project Structure

## 📁 Clean Project Organization

```
VigilantEye/
├── app/                          # Main application package
│   ├── __init__.py              # App factory & configuration
│   ├── controllers/             # Route controllers (blueprints)
│   │   ├── main.py             # Main web routes (/, /dashboard, /profile)
│   │   ├── web_auth_controller.py  # Web authentication (/login, /register)
│   │   ├── auth_controller.py  # API authentication (/api/auth/*)
│   │   ├── api.py              # General API routes
│   │   ├── video_controller.py # Video management API
│   │   ├── recording_controller.py  # Recording management API
│   │   └── project_controller.py    # Project management API
│   ├── models/                  # Database models
│   │   ├── user.py             # User model
│   │   ├── video.py            # Video model
│   │   ├── recording.py        # Recording model
│   │   ├── project.py          # Project model
│   │   ├── clip.py             # Clip model
│   │   ├── segment.py          # Segment model
│   │   ├── frame.py            # Frame model
│   │   ├── device.py           # Device model
│   │   ├── analytics.py        # Analytics model
│   │   └── base.py             # Base model
│   ├── schemas/                 # Marshmallow schemas for validation
│   │   ├── auth_schema.py      # Authentication schemas
│   │   ├── user_schema.py      # User schemas
│   │   └── ...                 # Other schemas
│   ├── templates/               # HTML templates (Jinja2)
│   │   ├── base.html           # Base layout template
│   │   ├── index.html          # Landing page
│   │   ├── dashboard.html      # Dashboard page
│   │   ├── profile.html        # User profile
│   │   └── auth/               # Authentication templates
│   │       ├── login.html      # Login page
│   │       └── register.html   # Registration page
│   ├── static/                  # Static files (CSS, JS, images)
│   │   ├── css/
│   │   │   └── style.css       # Custom styles
│   │   └── js/
│   │       └── script.js       # Custom JavaScript
│   └── utils/                   # Utility functions
│       └── auth_utils.py       # Authentication helpers
│
├── migrations/                  # Database migrations (Alembic)
│   ├── versions/               # Migration scripts
│   │   ├── 96b2b763b3c3_initial_migration.py
│   │   ├── 9b31b496ba4f_add_roles_and_site_id_to_user_model.py
│   │   └── fix_password_hash_length.py
│   ├── env.py                  # Migration environment
│   └── alembic.ini             # Alembic configuration
│
├── SriDatta/                    # Jupyter notebooks
│   └── EnvDet_1.ipynb
│
├── docker-compose.yml           # Docker Compose for local dev
├── docker-compose.local.yml    # Docker Compose for local testing
├── Dockerfile                   # Docker image definition
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── .gitignore                   # Git ignore rules
│
├── deploy.ps1                   # PowerShell deployment script
├── deploy.sh                    # Bash deployment script
├── test-local.ps1              # Local Docker testing (PowerShell)
└── test-local.sh               # Local Docker testing (Bash)
```

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview and getting started |
| `ROUTES_STRUCTURE.md` | Complete route mapping (API & Web) |
| `FRONTEND_INTEGRATION.md` | Frontend integration details |
| `DEPLOYMENT_GUIDE.md` | Azure deployment instructions |
| `DEPLOYMENT_STATUS.md` | Current deployment status |
| `LOCAL_TESTING_GUIDE.md` | Docker local testing guide |
| `QUICKSTART.md` | Quick start guide |
| `PROJECT_STRUCTURE.md` | This file - project organization |

## 🔑 Key Components

### Backend
- **Framework**: Flask
- **Database**: MySQL (Azure Database for MySQL)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Authentication**: Flask-JWT-Extended + Session-based
- **API**: RESTful with JSON responses

### Frontend
- **Templates**: Jinja2
- **CSS Framework**: Bootstrap 5.1.3
- **Icons**: Bootstrap Icons
- **JavaScript**: Vanilla JS (no framework)

### Deployment
- **Container**: Docker
- **Registry**: Azure Container Registry
- **Hosting**: Azure Container Instances
- **Database**: Azure Database for MySQL

## 🎯 Clean Code Practices

1. ✅ **Separation of Concerns**: Controllers, Models, Schemas separated
2. ✅ **DRY Principle**: Reusable templates and utilities
3. ✅ **Clear Naming**: Descriptive file and function names
4. ✅ **Documentation**: Comprehensive guides and inline comments
5. ✅ **Version Control**: .gitignore for clean repository

## 🚀 Quick Commands

### Development
```bash
# Run locally
python run.py

# Run with Docker
docker-compose up
```

### Database
```bash
# Create migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

### Deployment
```bash
# Deploy to Azure (PowerShell)
.\deploy.ps1

# Deploy to Azure (Bash)
./deploy.sh
```

### Testing
```bash
# Test locally with Docker
.\test-local.ps1
```

## 📦 Dependencies (requirements.txt)

- Flask - Web framework
- Flask-SQLAlchemy - ORM
- Flask-Migrate - Database migrations
- Flask-CORS - Cross-Origin Resource Sharing
- Flask-JWT-Extended - JWT authentication
- PyMySQL - MySQL driver
- marshmallow - Object serialization
- Werkzeug - Security utilities
- gunicorn - Production WSGI server

---

**Status**: ✅ Clean & Organized
**Last Updated**: October 9, 2025
