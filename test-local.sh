#!/bin/bash
# Bash script to test VIGILANTEye locally with Docker

set -e

echo "========================================"
echo "VIGILANTEye Local Docker Testing"
echo "========================================"
echo ""

# Check if Docker is running
echo "Checking Docker..."
docker --version
if [ $? -ne 0 ]; then
    echo "Error: Docker is not installed or not running!"
    exit 1
fi

echo "Docker is available!"
echo ""

# Stop and remove existing containers
echo "Cleaning up existing containers..."
docker-compose -f docker-compose.local.yml down -v
echo ""

# Build and start containers
echo "Building and starting containers..."
echo "This may take a few minutes on first run..."
echo ""
docker-compose -f docker-compose.local.yml up --build -d

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Containers started successfully!"
    echo "========================================"
    echo ""
    
    # Wait for application to be ready
    echo "Waiting for application to initialize (30 seconds)..."
    sleep 30
    
    echo ""
    echo "========================================"
    echo "Application is ready!"
    echo "========================================"
    echo ""
    
    echo "Access your application at:"
    echo "  Homepage:   http://localhost:8000"
    echo "  Login:      http://localhost:8000/login"
    echo "  Register:   http://localhost:8000/register"
    echo "  Dashboard:  http://localhost:8000/dashboard"
    echo "  API Health: http://localhost:8000/health"
    echo ""
    
    echo "Database connection:"
    echo "  Host: localhost:3306"
    echo "  Database: flaskapi"
    echo "  User: vigilanteye"
    echo "  Password: YourPassword123!"
    echo ""
    
    echo "========================================"
    echo "Useful Commands:"
    echo "========================================"
    echo "View logs:           docker-compose -f docker-compose.local.yml logs -f"
    echo "View app logs:       docker-compose -f docker-compose.local.yml logs -f app"
    echo "View db logs:        docker-compose -f docker-compose.local.yml logs -f db"
    echo "Stop containers:     docker-compose -f docker-compose.local.yml stop"
    echo "Start containers:    docker-compose -f docker-compose.local.yml start"
    echo "Restart containers:  docker-compose -f docker-compose.local.yml restart"
    echo "Remove containers:   docker-compose -f docker-compose.local.yml down -v"
    echo ""
    
    # Show logs
    echo "========================================"
    echo "Recent Application Logs:"
    echo "========================================"
    echo ""
    docker-compose -f docker-compose.local.yml logs --tail=50 app
    
    echo ""
    echo "========================================"
    echo "Testing API endpoint..."
    echo "========================================"
    echo ""
    
    sleep 5
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Health check successful!"
        curl http://localhost:8000/health
        echo ""
    else
        echo "Health check failed. Container may still be starting..."
        echo "Please wait a few more seconds and try: http://localhost:8000/health"
    fi
    
    echo ""
    echo "========================================"
    echo "To stop containers, run:"
    echo "docker-compose -f docker-compose.local.yml down"
    echo "========================================"
    echo ""
    
else
    echo ""
    echo "Failed to start containers!"
    echo "Check the error messages above."
    exit 1
fi
