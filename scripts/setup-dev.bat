@echo off
REM VigilantEye Windows Setup Script
REM This script sets up VigilantEye on Windows using Docker

echo ============================================
echo 🚀 VigilantEye Windows Setup
echo ============================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available. Please ensure Docker Desktop is running.
    pause
    exit /b 1
)

echo ✅ Docker is installed and ready
echo.

REM Create environment file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file...
    (
        echo # Database Configuration
        echo POSTGRES_DB=vigilanteye
        echo POSTGRES_USER=vigilanteye
        echo POSTGRES_PASSWORD=vigilanteye123
        echo.
        echo # Local Cache Configuration
        echo CACHE_DIR=storage/local_cache
        echo CACHE_MAX_MEMORY_ITEMS=1000
        echo CACHE_DEFAULT_TTL=3600
        echo CACHE_CLEANUP_INTERVAL=300
        echo.
        echo # Application Configuration
        echo SECRET_KEY=your-secret-key-change-in-production
        echo JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
        echo.
        echo # External APIs ^(Optional^)
        echo OPENAI_API_KEY=
        echo TELEGRAM_BOT_TOKEN=
        echo TELEGRAM_CHAT_ID=
        echo.
        echo # AI Configuration
        echo AI_DEVICE=cpu
        echo MODEL_CACHE_ENABLED=true
    ) > .env
    echo ✅ Created .env file
) else (
    echo 📝 .env file already exists
)

echo.

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist backend\storage mkdir backend\storage
if not exist backend\storage\videos mkdir backend\storage\videos
if not exist backend\storage\evidence mkdir backend\storage\evidence
if not exist backend\storage\model_cache mkdir backend\storage\model_cache
if not exist backend\storage\vector_db mkdir backend\storage\vector_db
if not exist backend\storage\local_cache mkdir backend\storage\local_cache
if not exist backend\logs mkdir backend\logs
if not exist nginx mkdir nginx

echo ✅ Directories created
echo.

REM Build and start services
echo 🔨 Building Docker images...
docker-compose build

if %errorlevel% neq 0 (
    echo ❌ Docker build failed
    pause
    exit /b 1
)

echo ✅ Docker images built successfully
echo.

echo 🚀 Starting services...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ❌ Failed to start services
    pause
    exit /b 1
)

echo ✅ Services started
echo.

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Check service health
echo 🏥 Checking service health...
echo.

REM Check backend health
curl -f http://localhost:8000/api/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend is healthy
) else (
    echo ❌ Backend health check failed
)

REM Check frontend health
curl -f http://localhost:3000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Frontend is healthy
) else (
    echo ❌ Frontend health check failed
)

REM Check database connection
docker-compose exec -T postgres pg_isready -U vigilanteye -d vigilanteye >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Database is ready
) else (
    echo ❌ Database connection failed
)

echo.

REM Setup database tables and default admin
echo 🗄️ Setting up database...
docker-compose exec backend python scripts/setup_database.py

if %errorlevel% equ 0 (
    echo ✅ Database setup completed
) else (
    echo ❌ Database setup failed
)

echo.

REM Check local cache directory
if exist backend\storage\local_cache (
    echo ✅ Local cache directory is ready
) else (
    echo ⚠️ Local cache directory will be created automatically
)

echo.

REM Show service URLs
echo ============================================
echo 🎉 Development environment is ready!
echo ============================================
echo.
echo 📱 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📊 API Documentation: http://localhost:8000/docs
echo 🏥 Health Check: http://localhost:8000/api/health
echo 📈 Detailed Metrics: http://localhost:8000/api/health/detailed
echo.

REM Show useful commands
echo 📋 Useful Commands:
echo   View logs: docker-compose logs -f
echo   Stop services: docker-compose down
echo   Restart services: docker-compose restart
echo   Rebuild images: docker-compose build --no-cache
echo   Access database: docker-compose exec postgres psql -U vigilanteye -d vigilanteye
echo   View cache stats: docker-compose exec backend python -c "from src.services.local_cache import get_cache; print(get_cache().get_stats())"
echo.

echo ============================================
echo ✨ Happy coding!
echo ============================================
echo.
echo Press any key to close this window...
pause >nul
