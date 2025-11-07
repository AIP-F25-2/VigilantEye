# VigilantEye Quick Start Guide

Get VigilantEye running in 5 minutes!

## 🚀 Prerequisites

- **Docker & Docker Compose** (recommended)
- **Node.js 18+** (for frontend development)
- **Python 3.11+** (for backend development)
- **Git** (for version control)

## 🗄️ Database Setup

### Quick Database Setup

VigilantEye uses MySQL. Here are the fastest ways to get it running:

#### Option 1: Docker (Easiest)
```bash
# Everything is automatic with Docker
docker-compose up -d
sleep 30  # Wait for MySQL to start
docker-compose exec backend python scripts/setup_database.py
```

#### Option 2: Local MySQL
```bash
# Install MySQL (Ubuntu/Debian)
sudo apt install mysql-server mysql-client

# Start MySQL
sudo systemctl start mysql

# Create database and user
mysql -u root -p
CREATE DATABASE vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vigilanteye'@'localhost' IDENTIFIED BY 'vigilanteye123';
GRANT ALL PRIVILEGES ON vigilanteye.* TO 'vigilanteye'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Setup schema
cd backend
python scripts/setup_database.py
```

#### Option 3: Docker MySQL Only
```bash
# Run MySQL in Docker
docker run -d --name vigilanteye-mysql \
  -e MYSQL_ROOT_PASSWORD=vigilanteye123 \
  -e MYSQL_DATABASE=vigilanteye \
  -e MYSQL_USER=vigilanteye \
  -e MYSQL_PASSWORD=vigilanteye123 \
  -p 3306:3306 mysql:8.0

# Wait and setup
sleep 30
export DATABASE_URL=mysql+pymysql://vigilanteye:vigilanteye123@localhost:3306/vigilanteye
cd backend && python scripts/setup_database.py
```

### Verify Database
```bash
# Test connection
mysql -u vigilanteye -pvigilanteye123 -h localhost vigilanteye

# Check if admin user exists
SELECT username, role FROM users WHERE role = 'admin';
```

## ⚡ Quick Start Options

### Option 1: Docker (Recommended - 2 minutes)

```bash
# Clone repository
git clone https://github.com/your-org/vigilanteye.git
cd vigilanteye

# Start everything with one command
docker-compose up -d

# Wait for services to start (30 seconds)
sleep 30

# Setup database
docker-compose exec backend python scripts/setup_database.py
```

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Automated Setup Script

```bash
# Clone repository
git clone https://github.com/your-org/vigilanteye.git
cd vigilanteye

# Run setup script (Linux/Mac)
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh

# Or run setup script (Windows)
scripts\setup-dev.bat
```

### Option 3: Windows Batch File

```cmd
# Double-click START_ALL.bat
# Or run from command prompt:
START_ALL.bat
```

### Option 4: Manual Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start backend
python run.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start frontend
npm run dev
```

## 🔧 Configuration

### Environment Variables

Create `.env` file in the root directory:

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

## 🧪 Testing the Setup

### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2. API Documentation
Open your browser and go to: http://localhost:8000/docs

### 3. Frontend Access
Open your browser and go to: http://localhost:3000

### 4. Test Authentication
```bash
# Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123",
    "role": "user"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword123"
  }'
```

## 🎯 Default Credentials

After running `setup_database.py`, you'll have:
- **Admin User**: `admin` / `admin123`
- **Database**: `vigilanteye` / `vigilanteye123`

## 📱 Application Features

### Dashboard
- Upload videos for AI analysis
- View recent threats and tickets
- Monitor system status

### Video Processing
- Upload video files
- Real-time processing status
- Download processed results

### Ticket Management
- View security incidents
- Manage evidence
- Download reports

### AI Analysis
- Face recognition
- Object detection
- Threat assessment
- Text extraction

## 🛠️ Useful Commands

### Docker Commands
```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Access backend container
docker-compose exec backend bash

# Access database
docker-compose exec mysql mysql -u vigilanteye -pvigilanteye123 vigilanteye
```

### Development Commands
```bash
# Run tests
docker-compose exec backend pytest tests/
docker-compose exec frontend npm test

# Check cache status
docker-compose exec backend python -c "from src.services.local_cache import get_cache; print(get_cache().get_stats())"

# View system metrics
curl http://localhost:8000/api/health/detailed
```

## 🚨 Troubleshooting

### Common Issues

#### "Port already in use"
```bash
# Check what's using the port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in .env
APP_PORT=8001
```

#### "Database connection failed"
```bash
# Check if MySQL is running
docker-compose exec mysql mysqladmin ping -h localhost -u vigilanteye -pvigilanteye123

# Reset database
docker-compose exec mysql mysql -u vigilanteye -pvigilanteye123 vigilanteye -e "DROP DATABASE vigilanteye; CREATE DATABASE vigilanteye;"
docker-compose exec backend python scripts/setup_database.py
```

#### "Module not found"
```bash
# Reinstall dependencies
docker-compose exec backend pip install -r requirements/development.txt
docker-compose exec frontend npm install
```

#### "Permission denied" (Linux/Mac)
```bash
# Fix script permissions
chmod +x scripts/setup-dev.sh
chmod +x scripts/deploy-azure.sh
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health
curl http://localhost:3000/health

# Database health
docker-compose exec mysql mysqladmin ping -h localhost -u vigilanteye -pvigilanteye123

# Cache health
docker-compose exec backend python -c "from src.services.local_cache import get_cache; print('Cache OK' if get_cache().get_stats() else 'Cache Error')"
```

## 🌐 Next Steps

### 1. Explore the Application
- Upload a test video
- Create a ticket
- Test AI analysis features

### 2. Customize Configuration
- Update environment variables
- Configure AI models
- Set up external APIs

### 3. Deploy to Production
- See `AZURE_DEPLOYMENT_GUIDE.md` for cloud deployment
- Configure SSL/TLS
- Set up monitoring

### 4. Development
- Check `backend/README.md` for backend details
- Check `frontend/README.md` for frontend details
- See `TESTING_AND_QUALITY_STANDARDS.md` for testing

## 📚 Additional Resources

- **Full Documentation**: `README.md`
- **Azure Deployment**: `AZURE_DEPLOYMENT_GUIDE.md`
- **Testing Guide**: `TESTING_AND_QUALITY_STANDARDS.md`
- **Backend API**: http://localhost:8000/docs
- **Frontend Source**: `frontend/src/`

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `docker-compose logs -f`
2. **Verify configuration**: Check `.env` file
3. **Test health endpoints**: Use the health check URLs
4. **Check prerequisites**: Ensure Docker and dependencies are installed
5. **Create an issue**: Use GitHub issues for bugs or feature requests

## 🎉 Success!

If everything is working, you should see:
- ✅ Backend running on http://localhost:8000
- ✅ Frontend running on http://localhost:3000
- ✅ Database connected and initialized
- ✅ Local cache working
- ✅ Health checks passing

**Happy coding!** 🚀

---

**Last Updated**: 2024-01-01  
**Version**: 1.0.0