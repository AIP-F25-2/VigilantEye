# VIGILANTEye Azure Deployment Script with Face & Identity Agent
# This script deploys the complete VIGILANTEye application with FaceAi integration

param(
    [string]$ResourceGroupName = "vigilanteye-rg",
    [string]$ContainerAppName = "vigilanteye-app",
    [string]$ContainerRegistryName = "vigilanteyeacr",
    [string]$Location = "eastus",
    [string]$ImageTag = "latest",
    [string]$Environment = "production"
)

Write-Host "🚀 Starting VIGILANTEye Azure Deployment with Face & Identity Agent..." -ForegroundColor Green

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed. Please install it from https://www.docker.com/get-started"
    exit 1
}

# Login to Azure (if not already logged in)
Write-Host "🔐 Checking Azure login status..." -ForegroundColor Yellow
$loginStatus = az account show 2>$null
if (-not $loginStatus) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
}

# Set the subscription
Write-Host "📋 Setting Azure subscription..." -ForegroundColor Yellow
az account set --subscription (az account show --query id -o tsv)

# Create resource group if it doesn't exist
Write-Host "📦 Creating resource group: $ResourceGroupName..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location --output none

# Create Azure Container Registry if it doesn't exist
Write-Host "🐳 Creating Azure Container Registry: $ContainerRegistryName..." -ForegroundColor Yellow
$acrExists = az acr show --name $ContainerRegistryName --resource-group $ResourceGroupName --query "name" -o tsv 2>$null
if (-not $acrExists) {
    az acr create --name $ContainerRegistryName --resource-group $ResourceGroupName --sku Basic --admin-enabled true --output none
    Write-Host "✅ Container Registry created successfully" -ForegroundColor Green
} else {
    Write-Host "✅ Container Registry already exists" -ForegroundColor Green
}

# Login to ACR
Write-Host "🔑 Logging into Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $ContainerRegistryName

# Get ACR login server
$acrLoginServer = az acr show --name $ContainerRegistryName --resource-group $ResourceGroupName --query "loginServer" -o tsv
Write-Host "📡 ACR Login Server: $acrLoginServer" -ForegroundColor Cyan

# Build Docker image
Write-Host "🔨 Building Docker image with Face & Identity Agent..." -ForegroundColor Yellow
$imageName = "$acrLoginServer/vigilanteye:$ImageTag"
Write-Host "📦 Image name: $imageName" -ForegroundColor Cyan

# Build the image
docker build -t $imageName . --no-cache

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker build failed"
    exit 1
}

Write-Host "✅ Docker image built successfully" -ForegroundColor Green

# Push image to ACR
Write-Host "📤 Pushing image to Azure Container Registry..." -ForegroundColor Yellow
docker push $imageName

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker push failed"
    exit 1
}

Write-Host "✅ Image pushed successfully" -ForegroundColor Green

# Create Container Apps Environment if it doesn't exist
Write-Host "🌍 Creating Container Apps Environment..." -ForegroundColor Yellow
$envName = "vigilanteye-env"
$envExists = az containerapp env show --name $envName --resource-group $ResourceGroupName --query "name" -o tsv 2>$null

if (-not $envExists) {
    az containerapp env create --name $envName --resource-group $ResourceGroupName --location $Location --output none
    Write-Host "✅ Container Apps Environment created successfully" -ForegroundColor Green
} else {
    Write-Host "✅ Container Apps Environment already exists" -ForegroundColor Green
}

# Get environment variables
Write-Host "🔧 Setting up environment variables..." -ForegroundColor Yellow

# Database configuration
$databaseUrl = "mysql+pymysql://vigilanteye:FlaskPass123!@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt"
$secretKey = "your-super-secret-key-for-production-2025"
$jwtSecretKey = "jwt-secret-key-for-production-2025"

# Telegram configuration
$telegramBotToken = "8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0"
$telegramWebhookSecret = "supersecret"

# Face & Identity Agent configuration
$faceSimilarityThreshold = "0.4"
$privacyMode = "false"
$cctvVideosDir = "app/cctv_videos"
$watchlistDir = "data/watchlists"

# Create or update Container App
Write-Host "🚀 Deploying Container App: $ContainerAppName..." -ForegroundColor Yellow

$containerAppExists = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query "name" -o tsv 2>$null

if ($containerAppExists) {
    Write-Host "📝 Updating existing Container App..." -ForegroundColor Yellow
    az containerapp update `
        --name $ContainerAppName `
        --resource-group $ResourceGroupName `
        --image $imageName `
        --set-env-vars `
            "DATABASE_URL=$databaseUrl" `
            "SECRET_KEY=$secretKey" `
            "JWT_SECRET_KEY=$jwtSecretKey" `
            "TELEGRAM_BOT_TOKEN=$telegramBotToken" `
            "TELEGRAM_WEBHOOK_SECRET=$telegramWebhookSecret" `
            "FACE_SIMILARITY_THRESHOLD=$faceSimilarityThreshold" `
            "PRIVACY_MODE=$privacyMode" `
            "CCTV_VIDEOS_DIR=$cctvVideosDir" `
            "WATCHLIST_DIR=$watchlistDir" `
            "FLASK_ENV=production" `
            "FLASK_DEBUG=0" `
        --cpu 2.0 `
        --memory 4.0Gi `
        --min-replicas 1 `
        --max-replicas 3 `
        --output none
} else {
    Write-Host "🆕 Creating new Container App..." -ForegroundColor Yellow
    az containerapp create `
        --name $ContainerAppName `
        --resource-group $ResourceGroupName `
        --environment $envName `
        --image $imageName `
        --target-port 8000 `
        --ingress external `
        --set-env-vars `
            "DATABASE_URL=$databaseUrl" `
            "SECRET_KEY=$secretKey" `
            "JWT_SECRET_KEY=$jwtSecretKey" `
            "TELEGRAM_BOT_TOKEN=$telegramBotToken" `
            "TELEGRAM_WEBHOOK_SECRET=$telegramWebhookSecret" `
            "FACE_SIMILARITY_THRESHOLD=$faceSimilarityThreshold" `
            "PRIVACY_MODE=$privacyMode" `
            "CCTV_VIDEOS_DIR=$cctvVideosDir" `
            "WATCHLIST_DIR=$watchlistDir" `
            "FLASK_ENV=production" `
            "FLASK_DEBUG=0" `
        --cpu 2.0 `
        --memory 4.0Gi `
        --min-replicas 1 `
        --max-replicas 3 `
        --output none
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Container App deployment failed"
    exit 1
}

Write-Host "✅ Container App deployed successfully" -ForegroundColor Green

# Get the application URL
Write-Host "🔍 Getting application URL..." -ForegroundColor Yellow
$appUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query "properties.configuration.ingress.fqdn" -o tsv

if ($appUrl) {
    Write-Host "🌐 Application URL: https://$appUrl" -ForegroundColor Green
    Write-Host "📱 FaceAi Dashboard: https://$appUrl/faceai" -ForegroundColor Cyan
    Write-Host "📹 CCTV Dashboard: https://$appUrl/cctv" -ForegroundColor Cyan
    Write-Host "🔗 API Health: https://$appUrl/health" -ForegroundColor Cyan
} else {
    Write-Warning "⚠️ Could not retrieve application URL"
}

# Run database migration
Write-Host "🗄️ Running database migration..." -ForegroundColor Yellow
try {
    az containerapp exec --name $ContainerAppName --resource-group $ResourceGroupName --command "flask db upgrade"
    Write-Host "✅ Database migration completed" -ForegroundColor Green
} catch {
    Write-Warning "⚠️ Database migration may need to be run manually"
}

# Test the deployment
Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
if ($appUrl) {
    try {
        $healthResponse = Invoke-RestMethod -Uri "https://$appUrl/health" -Method GET -TimeoutSec 30
        if ($healthResponse.status -eq "healthy") {
            Write-Host "✅ Health check passed" -ForegroundColor Green
        } else {
            Write-Warning "⚠️ Health check returned unexpected status: $($healthResponse.status)"
        }
    } catch {
        Write-Warning "⚠️ Health check failed: $($_.Exception.Message)"
    }
}

# Display deployment summary
Write-Host "`n🎉 VIGILANTEye Deployment Complete!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "📦 Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "🐳 Container Registry: $ContainerRegistryName" -ForegroundColor White
Write-Host "🌍 Container App: $ContainerAppName" -ForegroundColor White
Write-Host "🌐 Application URL: https://$appUrl" -ForegroundColor White
Write-Host "`n🔗 Key Endpoints:" -ForegroundColor Yellow
Write-Host "   • Main Dashboard: https://$appUrl/" -ForegroundColor Cyan
Write-Host "   • FaceAi Dashboard: https://$appUrl/faceai" -ForegroundColor Cyan
Write-Host "   • CCTV Intelligence: https://$appUrl/cctv" -ForegroundColor Cyan
Write-Host "   • API Health: https://$appUrl/health" -ForegroundColor Cyan
Write-Host "   • FaceAi API: https://$appUrl/api/faceai/status" -ForegroundColor Cyan
Write-Host "   • CCTV API: https://$appUrl/api/cctv/status" -ForegroundColor Cyan

Write-Host "`n🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test the FaceAi integration: https://$appUrl/faceai" -ForegroundColor White
Write-Host "2. Test CCTV processing: https://$appUrl/cctv" -ForegroundColor White
Write-Host "3. Upload CCTV videos for processing" -ForegroundColor White
Write-Host "4. Configure watchlists for employees, VIPs, and suspects" -ForegroundColor White
Write-Host "5. Monitor alerts and person tracking" -ForegroundColor White

Write-Host "`n✨ VIGILANTEye with Face & Identity Agent is now live!" -ForegroundColor Green

