@echo off
REM VigilantEye Setup Script with Telegram Configuration for Windows
REM This script sets up the environment with your Telegram credentials

echo 🚀 Setting up VigilantEye with Telegram integration...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

echo ✅ Docker and Docker Compose are installed

REM Create necessary directories
echo 📁 Creating storage directories...
if not exist "backend\storage\videos" mkdir backend\storage\videos
if not exist "backend\storage\evidence" mkdir backend\storage\evidence
if not exist "backend\storage\model_cache" mkdir backend\storage\model_cache
if not exist "backend\storage\vector_db" mkdir backend\storage\vector_db
if not exist "backend\storage\frames" mkdir backend\storage\frames
if not exist "backend\storage\audio" mkdir backend\storage\audio
if not exist "backend\storage\local_cache" mkdir backend\storage\local_cache
if not exist "backend\logs" mkdir backend\logs
echo ✅ Storage directories created

REM Create environment file with Telegram credentials
echo 🔧 Creating environment configuration...
(
echo # VigilantEye Environment Configuration
echo APP_NAME=VigilantEye
echo APP_ENV=development
echo APP_DEBUG=true
echo.
echo # Database Configuration
echo DATABASE_URL=postgresql://vigilanteye:vigilanteye123@postgres:5432/vigilanteye
echo.
echo # Security
echo SECRET_KEY=your-secret-key-change-in-production
echo JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
echo.
echo # Telegram Integration ^(Your Credentials^)
echo TELEGRAM_BOT_TOKEN=8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0
echo TELEGRAM_WEBHOOK_SECRET=supersecret
echo TELEGRAM_ESCALATION_CHANNEL=-4672336726
echo.
echo # AI Configuration
echo AI_DEVICE=cpu
echo MODEL_CACHE_ENABLED=true
echo MODEL_CACHE_PATH=storage/model_cache
echo.
echo # OpenAI API ^(Add your key here^)
echo OPENAI_API_KEY=your-openai-api-key-here
echo.
echo # Cleanup Configuration
echo CLEANUP_ENABLED=true
echo CLEANUP_INTERVAL_HOURS=24
echo PERSON_DATA_RETENTION_DAYS=30
echo EMBEDDING_DATA_RETENTION_DAYS=90
echo MEDIA_RETENTION_DAYS=60
echo.
echo # Storage Paths
echo EVIDENCE_STORAGE_PATH=storage/evidence
echo VECTOR_DB_PATH=storage/vector_db
echo VIDEO_STORAGE_PATH=storage/videos
echo FRAMES_STORAGE_PATH=storage/frames
echo AUDIO_STORAGE_PATH=storage/audio
) > backend\.env

echo ✅ Environment file created with your Telegram credentials

REM Build and start services
echo 🐳 Building and starting Docker services...
docker-compose build
docker-compose up -d

echo ✅ Docker services started

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Check service health
echo 🔍 Checking service health...

REM Setup database
echo 🗄️ Setting up database...
docker-compose exec backend python scripts/setup_database.py
echo ✅ Database setup completed

REM Check backend health
curl -f http://localhost:8000/api/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend is healthy
) else (
    echo ⚠️ Backend health check failed
)

REM Check frontend
curl -f http://localhost:3000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Frontend is healthy
) else (
    echo ⚠️ Frontend health check failed
)

echo.
echo 🎉 VigilantEye setup completed!
echo.
echo 📋 Access Information:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:8000
echo    API Documentation: http://localhost:8000/docs
echo.
echo 🔐 Default Login:
echo    Username: admin
echo    Password: admin123
echo.
echo 📱 Telegram Integration:
echo    Bot Token: 8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0
echo    Escalation Channel: -4672336726
echo    Webhook Secret: supersecret
echo.
echo 🛠️ Useful Commands:
echo    View logs: docker-compose logs -f
echo    Stop services: docker-compose down
echo    Restart services: docker-compose restart
echo    Check status: docker-compose ps
echo.
echo ✅ Setup completed successfully! 🚀
pause
