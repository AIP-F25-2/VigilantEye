# Azure Deployment Script for VIGILANTEye
# This script builds and deploys the application to Azure Container Apps

param(
    [string]$ResourceGroup = "vigilanteye-docker-rg",
    [string]$RegistryName = "vigilanteyeacr",
    [string]$ContainerAppName = "vigilanteye-app",
    [string]$ImageName = "vigilanteye:latest"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Azure Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build Docker image
Write-Host "[1/5] Building Docker image..." -ForegroundColor Yellow
$buildResult = az acr build --registry $RegistryName --image $ImageName --platform linux/amd64 --timeout 3600 .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host ""

# Step 2: Update Container App
Write-Host "[2/5] Updating Container App..." -ForegroundColor Yellow
$imageFullName = "${RegistryName}.azurecr.io/${ImageName}"
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --image $imageFullName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Container App update failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Container App updated successfully!" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for Container App to be ready
Write-Host "[3/5] Waiting for Container App to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "Container App should be ready now!" -ForegroundColor Green
Write-Host ""

# Step 4: Get Container App URL
Write-Host "[4/5] Getting Container App URL..." -ForegroundColor Yellow
$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host "Application URL: https://$fqdn" -ForegroundColor Cyan
Write-Host ""

# Step 5: Database migrations
Write-Host "[5/5] Database migrations..." -ForegroundColor Yellow
Write-Host "Note: Migrations run automatically on container startup." -ForegroundColor Green
Write-Host "Check logs to verify migrations completed successfully." -ForegroundColor Yellow
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URL: https://$fqdn" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the application at: https://$fqdn" -ForegroundColor White
Write-Host "2. Run database migrations if needed" -ForegroundColor White
Write-Host "3. Check logs: az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroup --follow" -ForegroundColor White
Write-Host ""
