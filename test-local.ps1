# PowerShell script to test VIGILANTEye locally with Docker

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Local Docker Testing" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not installed or not running!" -ForegroundColor Red
    exit 1
}

Write-Host "Docker is available!`n" -ForegroundColor Green

# Stop and remove existing containers
Write-Host "Cleaning up existing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.local.yml down -v
Write-Host ""

# Build and start containers
Write-Host "Building and starting containers..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run...`n" -ForegroundColor Cyan
docker-compose -f docker-compose.local.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Containers started successfully!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # Wait for application to be ready
    Write-Host "Waiting for application to initialize (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Application is ready!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Write-Host "Access your application at:" -ForegroundColor Yellow
    Write-Host "  Homepage:   http://localhost:8000" -ForegroundColor White
    Write-Host "  Login:      http://localhost:8000/login" -ForegroundColor White
    Write-Host "  Register:   http://localhost:8000/register" -ForegroundColor White
    Write-Host "  Dashboard:  http://localhost:8000/dashboard" -ForegroundColor White
    Write-Host "  API Health: http://localhost:8000/health`n" -ForegroundColor White
    
    Write-Host "Database connection:" -ForegroundColor Yellow
    Write-Host "  Host: localhost:3306" -ForegroundColor White
    Write-Host "  Database: flaskapi" -ForegroundColor White
    Write-Host "  User: vigilanteye" -ForegroundColor White
    Write-Host "  Password: YourPassword123!`n" -ForegroundColor White
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Useful Commands:" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "View logs:           docker-compose -f docker-compose.local.yml logs -f" -ForegroundColor White
    Write-Host "View app logs:       docker-compose -f docker-compose.local.yml logs -f app" -ForegroundColor White
    Write-Host "View db logs:        docker-compose -f docker-compose.local.yml logs -f db" -ForegroundColor White
    Write-Host "Stop containers:     docker-compose -f docker-compose.local.yml stop" -ForegroundColor White
    Write-Host "Start containers:    docker-compose -f docker-compose.local.yml start" -ForegroundColor White
    Write-Host "Restart containers:  docker-compose -f docker-compose.local.yml restart" -ForegroundColor White
    Write-Host "Remove containers:   docker-compose -f docker-compose.local.yml down -v`n" -ForegroundColor White
    
    # Show logs
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Recent Application Logs:" -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Cyan
    docker-compose -f docker-compose.local.yml logs --tail=50 app
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Testing API endpoint..." -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
        Write-Host "Health check successful!" -ForegroundColor Green
        Write-Host "Response: $($response | ConvertTo-Json)" -ForegroundColor White
    } catch {
        Write-Host "Health check failed. Container may still be starting..." -ForegroundColor Yellow
        Write-Host "Please wait a few more seconds and try: http://localhost:8000/health" -ForegroundColor White
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "To stop containers, run:" -ForegroundColor Yellow
    Write-Host "docker-compose -f docker-compose.local.yml down" -ForegroundColor White
    Write-Host "========================================`n" -ForegroundColor Cyan
    
} else {
    Write-Host "`nFailed to start containers!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    exit 1
}
