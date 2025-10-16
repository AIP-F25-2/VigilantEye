# Azure Deployment Script for VIGILANTEye with Telegram Integration
# This script deploys the application to Azure Container Apps

Write-Host "🚀 Starting Azure Deployment for VIGILANTEye with Telegram Integration" -ForegroundColor Green

# Configuration
$RESOURCE_GROUP = "vigilanteye-docker-rg"
$ACR_NAME = "vigilanteyeacr"
$CONTAINER_APP_NAME = "vigilanteye-app"
$LOCATION = "eastus"

Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $RESOURCE_GROUP"
Write-Host "  ACR Name: $ACR_NAME"
Write-Host "  Container App: $CONTAINER_APP_NAME"
Write-Host "  Location: $LOCATION"

# Step 1: Build Docker image
Write-Host "`n🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t $ACR_NAME.azurecr.io/vigilanteye-web:latest .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker image built successfully" -ForegroundColor Green

# Step 2: Login to ACR
Write-Host "`n🔐 Logging into Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $ACR_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ACR login failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Successfully logged into ACR" -ForegroundColor Green

# Step 3: Push image to ACR
Write-Host "`n📤 Pushing image to Azure Container Registry..." -ForegroundColor Yellow
docker push $ACR_NAME.azurecr.io/vigilanteye-web:latest

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Image push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Image pushed successfully to ACR" -ForegroundColor Green

# Step 4: Update Container App
Write-Host "`n🔄 Updating Azure Container App..." -ForegroundColor Yellow
az containerapp update `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --image $ACR_NAME.azurecr.io/vigilanteye-web:latest `
    --set-env-vars `
        TELEGRAM_BOT_TOKEN="8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0" `
        TELEGRAM_WEBHOOK_SECRET="supersecret" `
        ALT_CHANNELS_FILE="alternate_channels.json" `
        ESCALATE_AFTER_SECONDS="900" `
        CLOSE_AFTER_SECONDS="3600" `
        FLASK_DEBUG="0"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Container App update failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container App updated successfully" -ForegroundColor Green

# Step 5: Run database migration
Write-Host "`n🗄️ Running database migration..." -ForegroundColor Yellow
az containerapp exec `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --command "flask db upgrade"

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Database migration may have failed, but continuing..." -ForegroundColor Yellow
}

# Step 6: Get application URL
Write-Host "`n🌐 Getting application URL..." -ForegroundColor Yellow
$APP_URL = az containerapp show `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host "✅ Application URL: https://$APP_URL" -ForegroundColor Green

# Step 7: Test application
Write-Host "`n🧪 Testing application..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://$APP_URL/health" -TimeoutSec 30
    Write-Host "✅ Health check passed: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Health check failed, but deployment completed" -ForegroundColor Yellow
}

# Step 8: Display summary
Write-Host "`n🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "Application URL: https://$APP_URL" -ForegroundColor Cyan
Write-Host "Health Check: https://$APP_URL/health" -ForegroundColor Cyan
Write-Host "Dashboard: https://$APP_URL/dashboard" -ForegroundColor Cyan
Write-Host "Telegram API: https://$APP_URL/api/telegram/ingest" -ForegroundColor Cyan
Write-Host "Webhook: https://$APP_URL/webhook/telegram/supersecret" -ForegroundColor Cyan

Write-Host "`n📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure your Telegram channels in alternate_channels.json"
Write-Host "2. Set up webhook URL: https://$APP_URL/webhook/telegram/supersecret"
Write-Host "3. Test the Telegram integration"
Write-Host "4. Monitor the application logs"

Write-Host "`n🔧 Useful Commands:" -ForegroundColor Yellow
Write-Host "View logs: az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP"
Write-Host "Update env: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --set-env-vars KEY=VALUE"
Write-Host "Scale app: az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 1 --max-replicas 3"

Write-Host "`n✅ VIGILANTEye with Telegram Integration deployed successfully!" -ForegroundColor Green
