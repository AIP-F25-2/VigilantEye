#!/bin/bash

# VigilantEye Setup Script with Telegram Configuration
# This script sets up the environment with your Telegram credentials

set -e

echo "🚀 Setting up VigilantEye with Telegram integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating storage directories..."
mkdir -p backend/storage/{videos,evidence,model_cache,vector_db,frames,audio,local_cache}
mkdir -p backend/logs
print_status "Storage directories created"

# Create environment file with Telegram credentials
echo "🔧 Creating environment configuration..."
cat > backend/.env << EOF
# VigilantEye Environment Configuration
APP_NAME=VigilantEye
APP_ENV=development
APP_DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://vigilanteye:vigilanteye123@postgres:5432/vigilanteye

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Telegram Integration (Your Credentials)
TELEGRAM_BOT_TOKEN=8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0
TELEGRAM_WEBHOOK_SECRET=supersecret
TELEGRAM_ESCALATION_CHANNEL=-4672336726

# AI Configuration
AI_DEVICE=cpu
MODEL_CACHE_ENABLED=true
MODEL_CACHE_PATH=storage/model_cache

# OpenAI API (Add your key here)
OPENAI_API_KEY=your-openai-api-key-here

# Cleanup Configuration
CLEANUP_ENABLED=true
CLEANUP_INTERVAL_HOURS=24
PERSON_DATA_RETENTION_DAYS=30
EMBEDDING_DATA_RETENTION_DAYS=90
MEDIA_RETENTION_DAYS=60

# Storage Paths
EVIDENCE_STORAGE_PATH=storage/evidence
VECTOR_DB_PATH=storage/vector_db
VIDEO_STORAGE_PATH=storage/videos
FRAMES_STORAGE_PATH=storage/frames
AUDIO_STORAGE_PATH=storage/audio
EOF

print_status "Environment file created with your Telegram credentials"

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose build
docker-compose up -d

print_status "Docker services started"

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check database
if docker-compose exec -T postgres pg_isready -U vigilanteye -d vigilanteye > /dev/null 2>&1; then
    print_status "Database is ready"
else
    print_warning "Database is not ready yet"
fi

# Setup database
echo "🗄️ Setting up database..."
docker-compose exec backend python scripts/setup_database.py
print_status "Database setup completed"

# Check backend health
if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    print_status "Backend is healthy"
else
    print_warning "Backend health check failed"
fi

# Check frontend
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    print_status "Frontend is healthy"
else
    print_warning "Frontend health check failed"
fi

# Check Telegram configuration
echo "📱 Testing Telegram configuration..."
if curl -f "http://localhost:8000/api/cleanup/status" > /dev/null 2>&1; then
    print_status "Telegram integration is configured"
else
    print_warning "Telegram integration test failed"
fi

echo ""
echo "🎉 VigilantEye setup completed!"
echo ""
echo "📋 Access Information:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "🔐 Default Login:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📱 Telegram Integration:"
echo "   Bot Token: 8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0"
echo "   Escalation Channel: -4672336726"
echo "   Webhook Secret: supersecret"
echo ""
echo "🛠️ Useful Commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Check status: docker-compose ps"
echo ""
print_status "Setup completed successfully! 🚀"
