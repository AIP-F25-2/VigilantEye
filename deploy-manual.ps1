# Manual Deployment Script for VIGILANTEye
# Comprehensive deployment guide with both interactive and automated options

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Manual Deployment Guide" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[Prerequisites Check]" -ForegroundColor Yellow
$prerequisites = @(
    @{Name="Docker"; Command="docker --version"},
    @{Name="Azure CLI"; Command="az --version"},
    @{Name="Python"; Command="python --version"}
)

foreach ($prereq in $prerequisites) {
    try {
        $output = Invoke-Expression $prereq.Command 2>&1
        Write-Host "  ✅ $($prereq.Name) installed" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $($prereq.Name) not found. Please install it first." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Deployment Steps" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check build status (if using ACR tasks)
Write-Host "[1/6] Checking build status..." -ForegroundColor Yellow
try {
    $buildStatus = az acr task list-runs --registry vigilanteyeacr --query "[0].status" --output tsv 2>$null
    if ($buildStatus) {
        Write-Host "Build Status: $buildStatus" -ForegroundColor $(if ($buildStatus -eq "Succeeded") { "Green" } else { "Yellow" })
    }
} catch {
    Write-Host "  ℹ️  ACR task check skipped (not using ACR tasks)" -ForegroundColor Gray
}

# Step 2: Environment Setup
Write-Host ""
Write-Host "[2/6] Environment Setup" -ForegroundColor Yellow
Write-Host "   Required environment variables:"
Write-Host "     - DATABASE_URL"
Write-Host "     - SECRET_KEY"
Write-Host "     - JWT_SECRET_KEY"
Write-Host "     - TELEGRAM_BOT_TOKEN"
Write-Host "     - TELEGRAM_WEBHOOK_SECRET"

# Step 3: Build Docker Image
Write-Host ""
Write-Host "[3/6] Build Docker Image" -ForegroundColor Yellow
Write-Host "   docker build -t vigilanteye:latest ."

# Step 4: Push to ACR
Write-Host ""
Write-Host "[4/6] Push to Azure Container Registry" -ForegroundColor Yellow
Write-Host "   az acr login --name vigilanteyeacr"
Write-Host "   docker tag vigilanteye:latest vigilanteyeacr.azurecr.io/vigilanteye-web:latest"
Write-Host "   docker push vigilanteyeacr.azurecr.io/vigilanteye-web:latest"

# Step 5: Update Container App
Write-Host ""
Write-Host "[5/6] Update Azure Container App" -ForegroundColor Yellow
az containerapp update `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "Container App update failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Container App updated!" -ForegroundColor Green

# Step 6: Wait and get URL
Write-Host ""
Write-Host "[6/6] Waiting for restart and getting URL..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

$url = az containerapp show `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host "Application URL: https://$url" -ForegroundColor Cyan

# Run migrations
Write-Host ""
Write-Host "[Migration] Running database migrations..." -ForegroundColor Yellow
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
Write-Host "📚 Additional Resources:" -ForegroundColor Yellow
Write-Host "   - README.md - Full documentation"
Write-Host "   - deploy-azure.ps1 - Automated deployment script"
Write-Host ""

