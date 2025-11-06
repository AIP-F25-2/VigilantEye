# Manual Deployment Script
# Run this after the Docker build completes

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Manual Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check build status
Write-Host "[1/5] Checking build status..." -ForegroundColor Yellow
$buildStatus = az acr task list-runs --registry vigilanteyeacr --query "[0].status" --output tsv
Write-Host "Build Status: $buildStatus" -ForegroundColor $(if ($buildStatus -eq "Succeeded") { "Green" } else { "Yellow" })

if ($buildStatus -ne "Succeeded") {
    Write-Host "WARNING: Build is not complete yet. Please wait for build to finish." -ForegroundColor Yellow
    Write-Host "Check status with: az acr task list-runs --registry vigilanteyeacr --output table --top 1" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

# Step 2: Update Container App
Write-Host ""
Write-Host "[2/5] Updating Container App..." -ForegroundColor Yellow
az containerapp update `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --image vigilanteyeacr.azurecr.io/vigilanteye:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "Container App update failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Container App updated!" -ForegroundColor Green

# Step 3: Wait for restart
Write-Host ""
Write-Host "[3/5] Waiting for Container App to restart (60 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60
Write-Host "Wait complete!" -ForegroundColor Green

# Step 4: Get URL
Write-Host ""
Write-Host "[4/5] Getting application URL..." -ForegroundColor Yellow
$url = az containerapp show `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host "Application URL: https://$url" -ForegroundColor Cyan

# Step 5: Run migrations
Write-Host ""
Write-Host "[5/5] Running database migrations..." -ForegroundColor Yellow
az containerapp exec `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --command "flask db upgrade"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migrations completed!" -ForegroundColor Green
} else {
    Write-Host "Migration may have failed. Check logs if needed." -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URL: https://$url" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the application:" -ForegroundColor Yellow
Write-Host "  Invoke-RestMethod -Uri `"https://$url/health`" -Method GET" -ForegroundColor White
Write-Host ""

