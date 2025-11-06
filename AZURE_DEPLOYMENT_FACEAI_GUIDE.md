# 🚀 VIGILANTEye Azure Deployment Guide - Face & Identity Agent

## 🎯 Overview

This guide provides step-by-step instructions for deploying VIGILANTEye with the new Face & Identity Agent to Azure Container Apps.

## 📋 Prerequisites

### Required Software
- **Azure CLI**: [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Docker**: [Install Docker Desktop](https://www.docker.com/get-started)
- **PowerShell**: Windows PowerShell 5.1+ or PowerShell Core 6+
- **Git**: [Install Git](https://git-scm.com/downloads)

### Azure Resources
- **Azure Subscription**: Active subscription with sufficient credits
- **Resource Group**: `vigilanteye-rg` (will be created if not exists)
- **Container Registry**: `vigilanteyeacr` (will be created if not exists)
- **Container Apps Environment**: `vigilanteye-env` (will be created if not exists)
- **MySQL Database**: Existing Azure MySQL server

## 🚀 Quick Deployment

### Option 1: Automated Deployment (Recommended)

```powershell
# Clone the repository
git clone <your-repository-url>
cd VIGILANTEye

# Run the deployment script
.\deploy-azure-faceai.ps1
```

### Option 2: Manual Deployment

Follow the step-by-step manual deployment process below.

## 📝 Manual Deployment Steps

### 1. **Prepare Environment**

```powershell
# Set variables
$ResourceGroupName = "vigilanteye-rg"
$ContainerAppName = "vigilanteye-app"
$ContainerRegistryName = "vigilanteyeacr"
$Location = "eastus"
$ImageTag = "latest"

# Login to Azure
az login

# Set subscription
az account set --subscription <your-subscription-id>
```

### 2. **Create Azure Resources**

```powershell
# Create resource group
az group create --name $ResourceGroupName --location $Location

# Create Container Registry
az acr create --name $ContainerRegistryName --resource-group $ResourceGroupName --sku Basic --admin-enabled true

# Create Container Apps Environment
az containerapp env create --name "vigilanteye-env" --resource-group $ResourceGroupName --location $Location
```

### 3. **Build and Push Docker Image**

```powershell
# Login to ACR
az acr login --name $ContainerRegistryName

# Get ACR login server
$acrLoginServer = az acr show --name $ContainerRegistryName --resource-group $ResourceGroupName --query "loginServer" -o tsv

# Build image
docker build -t "$acrLoginServer/vigilanteye:$ImageTag" .

# Push image
docker push "$acrLoginServer/vigilanteye:$ImageTag"
```

### 4. **Deploy Container App**

```powershell
# Deploy Container App
az containerapp create `
    --name $ContainerAppName `
    --resource-group $ResourceGroupName `
    --environment "vigilanteye-env" `
    --image "$acrLoginServer/vigilanteye:$ImageTag" `
    --target-port 8000 `
    --ingress external `
    --set-env-vars `
        "DATABASE_URL=mysql+pymysql://vigilanteye:FlaskPass123!@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt" `
        "SECRET_KEY=your-super-secret-key-for-production-2025" `
        "JWT_SECRET_KEY=jwt-secret-key-for-production-2025" `
        "TELEGRAM_BOT_TOKEN=8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0" `
        "TELEGRAM_WEBHOOK_SECRET=supersecret" `
        "FACE_SIMILARITY_THRESHOLD=0.4" `
        "PRIVACY_MODE=false" `
        "CCTV_VIDEOS_DIR=app/cctv_videos" `
        "WATCHLIST_DIR=data/watchlists" `
        "FLASK_ENV=production" `
        "FLASK_DEBUG=0" `
    --cpu 2.0 `
    --memory 4.0Gi `
    --min-replicas 1 `
    --max-replicas 3
```

### 5. **Run Database Migration**

```powershell
# Run migration
az containerapp exec --name $ContainerAppName --resource-group $ResourceGroupName --command "flask db upgrade"
```

## 🔧 Configuration

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | MySQL connection string | Database connection with SSL |
| `SECRET_KEY` | Random secret key | Flask secret key |
| `JWT_SECRET_KEY` | JWT secret | JWT token secret |
| `TELEGRAM_BOT_TOKEN` | Bot token | Telegram bot integration |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret | Telegram webhook security |
| `FACE_SIMILARITY_THRESHOLD` | 0.4 | Face recognition threshold |
| `PRIVACY_MODE` | false | Enable/disable demographics |
| `CCTV_VIDEOS_DIR` | app/cctv_videos | CCTV videos directory |
| `WATCHLIST_DIR` | data/watchlists | Watchlist storage directory |

### Resource Configuration

- **CPU**: 2.0 cores
- **Memory**: 4.0 GiB
- **Min Replicas**: 1
- **Max Replicas**: 3
- **Target Port**: 8000
- **Ingress**: External (public)

## 🧪 Testing Deployment

### 1. **Health Check**

```bash
curl https://your-app-url.azurecontainerapps.io/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "message": "API is operational"
}
```

### 2. **FaceAi Service Status**

```bash
curl https://your-app-url.azurecontainerapps.io/api/faceai/status
```

**Expected Response:**
```json
{
  "success": true,
  "status": {
    "initialized": true,
    "face_detector": true,
    "demographics_analyzer": true,
    "ambiguity_checker": true,
    "available": true
  }
}
```

### 3. **CCTV Agent Status**

```bash
curl https://your-app-url.azurecontainerapps.io/api/cctv/status
```

**Expected Response:**
```json
{
  "success": true,
  "agent_status": "active",
  "tracking_summary": {
    "total_persons": 0,
    "watchlist_persons": 0,
    "cameras_active": 0
  }
}
```

## 🌐 Access Points

### Web Interfaces
- **Main Dashboard**: `https://your-app-url.azurecontainerapps.io/`
- **FaceAi Dashboard**: `https://your-app-url.azurecontainerapps.io/faceai`
- **CCTV Intelligence**: `https://your-app-url.azurecontainerapps.io/cctv`

### API Endpoints
- **Health Check**: `https://your-app-url.azurecontainerapps.io/health`
- **FaceAi API**: `https://your-app-url.azurecontainerapps.io/api/faceai/*`
- **CCTV API**: `https://your-app-url.azurecontainerapps.io/api/cctv/*`
- **Telegram API**: `https://your-app-url.azurecontainerapps.io/api/telegram/*`

## 🔍 Monitoring

### Azure Container Apps Monitoring

1. **Navigate to Azure Portal**
2. **Go to Container Apps**
3. **Select your app**
4. **View Metrics and Logs**

### Application Logs

```powershell
# View logs
az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroupName --follow
```

### Performance Metrics

- **CPU Usage**: Monitor CPU utilization
- **Memory Usage**: Track memory consumption
- **Request Rate**: Monitor API requests
- **Error Rate**: Track application errors

## 🚨 Troubleshooting

### Common Issues

#### 1. **Docker Build Fails**
```bash
# Check Docker daemon
docker info

# Clean Docker cache
docker system prune -a

# Rebuild with verbose output
docker build -t vigilanteye:latest . --no-cache --progress=plain
```

#### 2. **Container App Fails to Start**
```powershell
# Check logs
az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroupName

# Check environment variables
az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query "properties.template.containers[0].env"
```

#### 3. **Database Connection Issues**
```powershell
# Test database connection
az containerapp exec --name $ContainerAppName --resource-group $ResourceGroupName --command "python -c 'from app import db; print(db.engine.url)'"
```

#### 4. **Face Recognition Not Working**
```powershell
# Check FaceAi service status
az containerapp exec --name $ContainerAppName --resource-group $ResourceGroupName --command "python -c 'from app.services.faceai_service import get_faceai_service; print(get_faceai_service().get_service_status())'"
```

### Performance Issues

#### 1. **High CPU Usage**
- Increase CPU allocation
- Optimize face recognition parameters
- Reduce frame processing rate

#### 2. **Memory Issues**
- Increase memory allocation
- Optimize image processing
- Clear face encoding cache

#### 3. **Slow Response Times**
- Enable auto-scaling
- Optimize database queries
- Use Redis caching

## 🔄 Updates and Maintenance

### Update Application

```powershell
# Build new image
docker build -t "$acrLoginServer/vigilanteye:latest" .

# Push new image
docker push "$acrLoginServer/vigilanteye:latest"

# Update Container App
az containerapp update --name $ContainerAppName --resource-group $ResourceGroupName --image "$acrLoginServer/vigilanteye:latest"
```

### Database Migration

```powershell
# Run new migrations
az containerapp exec --name $ContainerAppName --resource-group $ResourceGroupName --command "flask db upgrade"
```

### Backup and Recovery

```powershell
# Backup database
az mysql server export --resource-group $ResourceGroupName --server-name vigilanteye-mysql --name backup-$(Get-Date -Format "yyyyMMdd-HHmmss")

# Restore database
az mysql server import --resource-group $ResourceGroupName --server-name vigilanteye-mysql --name backup-file --storage-uri "https://storageaccount.blob.core.windows.net/backups/backup-file.sql"
```

## 📊 Cost Optimization

### Resource Optimization

1. **Right-size Resources**: Monitor usage and adjust CPU/memory
2. **Auto-scaling**: Configure appropriate min/max replicas
3. **Scheduled Scaling**: Scale down during off-hours
4. **Storage Optimization**: Clean up old logs and temporary files

### Monitoring Costs

```powershell
# View resource costs
az consumption usage list --billing-period-name "202501-202501" --query "[].{Resource:instanceName, Cost:pretaxCost}" --output table
```

## 🔒 Security Considerations

### Network Security
- **HTTPS Only**: All traffic encrypted
- **Private Endpoints**: Consider for database access
- **Firewall Rules**: Restrict database access

### Data Protection
- **Encryption at Rest**: Database encryption enabled
- **Encryption in Transit**: SSL/TLS for all connections
- **Secrets Management**: Use Azure Key Vault for sensitive data

### Access Control
- **RBAC**: Role-based access control
- **API Authentication**: JWT token-based authentication
- **Admin Access**: Limit administrative access

## 🎯 Next Steps

### Post-Deployment Tasks

1. **Test All Features**:
   - Upload and process CCTV videos
   - Test face detection and recognition
   - Configure watchlists
   - Test Telegram integration

2. **Configure Monitoring**:
   - Set up alerts for errors
   - Monitor performance metrics
   - Configure log retention

3. **Security Hardening**:
   - Update default passwords
   - Configure firewall rules
   - Enable audit logging

4. **Backup Strategy**:
   - Set up automated backups
   - Test restore procedures
   - Document recovery processes

---

**VIGILANTEye with Face & Identity Agent is now successfully deployed on Azure!** 🎉

Your multi-agent video intelligence system is ready for production use with advanced face detection, recognition, and watchlist management capabilities.

