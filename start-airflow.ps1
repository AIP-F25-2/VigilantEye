# Start Apache Airflow for VIGILANTEye

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Apache Airflow" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is available`n" -ForegroundColor Green

# Set Airflow UID
$env:AIRFLOW_UID = 50000

# Start Airflow
Write-Host "Starting Airflow services..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes on first run...`n" -ForegroundColor Cyan

docker-compose -f docker-compose.airflow.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "✅ Airflow Started Successfully!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Write-Host "Waiting for Airflow to initialize (60 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 60
    
    Write-Host "`nAirflow UI:" -ForegroundColor Yellow
    Write-Host "  URL: http://localhost:8080" -ForegroundColor White
    Write-Host "  Username: admin" -ForegroundColor White
    Write-Host "  Password: admin123`n" -ForegroundColor White
    
    Write-Host "Available DAGs:" -ForegroundColor Yellow
    Write-Host "  1. video_processing_pipeline - Process videos (hourly)" -ForegroundColor White
    Write-Host "  2. analytics_pipeline - Generate analytics (daily 2 AM)" -ForegroundColor White
    Write-Host "  3. database_maintenance - DB cleanup (daily 3 AM)`n" -ForegroundColor White
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Useful Commands:" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "View logs:     docker-compose -f docker-compose.airflow.yml logs -f" -ForegroundColor White
    Write-Host "Stop Airflow:  docker-compose -f docker-compose.airflow.yml down" -ForegroundColor White
    Write-Host "Restart:       docker-compose -f docker-compose.airflow.yml restart" -ForegroundColor White
    Write-Host "Status:        docker-compose -f docker-compose.airflow.yml ps`n" -ForegroundColor White
    
    Write-Host "Opening Airflow UI..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    start http://localhost:8080
    
} else {
    Write-Host "`n❌ Failed to start Airflow!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    exit 1
}
