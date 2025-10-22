#!/bin/bash

# VigilantEye Development Setup Script
# This script sets up the development environment using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up VigilantEye Development Environment${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file...${NC}"
    cat > .env << EOF
# Database Configuration
POSTGRES_DB=vigilanteye
POSTGRES_USER=vigilanteye
POSTGRES_PASSWORD=vigilanteye123

# Redis Configuration
REDIS_PASSWORD=vigilanteye123

# Application Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# External APIs (Optional)
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# AI Configuration
AI_DEVICE=cpu
MODEL_CACHE_ENABLED=true
EOF
    echo -e "${GREEN}✅ Created .env file${NC}"
else
    echo -e "${YELLOW}📝 .env file already exists${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p backend/storage/videos
mkdir -p backend/storage/evidence
mkdir -p backend/storage/model_cache
mkdir -p backend/storage/vector_db
mkdir -p backend/logs
mkdir -p nginx

echo -e "${GREEN}✅ Directories created${NC}"

# Build and start services
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Check service health
echo -e "${YELLOW}🏥 Checking service health...${NC}"

# Check backend health
if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
fi

# Check frontend health
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is healthy${NC}"
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
fi

# Check database connection
if docker-compose exec -T postgres pg_isready -U vigilanteye -d vigilanteye > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database is ready${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
fi

# Setup database tables and default admin
echo -e "${YELLOW}🗄️ Setting up database...${NC}"
docker-compose exec backend python scripts/setup_database.py

# Check Redis connection
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
fi

# Show service URLs
echo -e "${GREEN}🎉 Development environment is ready!${NC}"
echo -e "${BLUE}📱 Frontend: http://localhost:3000${NC}"
echo -e "${BLUE}🔧 Backend API: http://localhost:8000${NC}"
echo -e "${BLUE}📊 API Documentation: http://localhost:8000/docs${NC}"
echo -e "${BLUE}🏥 Health Check: http://localhost:8000/api/health${NC}"
echo -e "${BLUE}📈 Detailed Metrics: http://localhost:8000/api/health/detailed${NC}"

# Show useful commands
echo -e "${YELLOW}📋 Useful Commands:${NC}"
echo -e "${BLUE}  View logs: docker-compose logs -f${NC}"
echo -e "${BLUE}  Stop services: docker-compose down${NC}"
echo -e "${BLUE}  Restart services: docker-compose restart${NC}"
echo -e "${BLUE}  Rebuild images: docker-compose build --no-cache${NC}"
echo -e "${BLUE}  Access database: docker-compose exec postgres psql -U vigilanteye -d vigilanteye${NC}"
echo -e "${BLUE}  Access Redis: docker-compose exec redis redis-cli${NC}"

echo -e "${GREEN}✨ Happy coding!${NC}"
