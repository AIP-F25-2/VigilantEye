# Azure Cloud Deployment Guide

## 🚀 Complete Azure Deployment Guide for VigilantEye

This guide provides comprehensive instructions for deploying VigilantEye to Azure Cloud using containers.

## 📋 Prerequisites

### Required Tools
- **Azure CLI** (latest version)
- **Docker** (latest version)
- **Git** (for cloning repository)
- **Azure Subscription** with appropriate permissions

### Azure Account Setup
1. **Create Azure Account**: https://azure.microsoft.com/free/
2. **Install Azure CLI**: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
3. **Login to Azure**: `az login`

## 🏗️ Deployment Options

### Option 1: Azure Container Instances (ACI) - Quick Start
Best for: Development, testing, small-scale deployments

### Option 2: Azure Kubernetes Service (AKS) - Production
Best for: Production, high availability, auto-scaling

### Option 3: Azure App Service - Managed
Best for: Simple deployments, managed infrastructure

## 🚀 Option 1: Azure Container Instances (ACI)

### Step 1: Automated Deployment

```bash
# Clone repository
git clone https://github.com/your-org/vigilanteye.git
cd vigilanteye

# Make script executable
chmod +x scripts/deploy-azure.sh

# Run deployment script
./scripts/deploy-azure.sh
```

### Step 2: Manual ACI Deployment

#### 1. Create Resource Group
```bash
az group create \
  --name vigilanteye-rg \
  --location eastus
```

#### 2. Deploy Infrastructure
```bash
az deployment group create \
  --resource-group vigilanteye-rg \
  --template-file azure/arm-template.json \
  --parameters appName=vigilanteye environment=production \
  --parameters adminUsername=vigilanteye adminPassword='VigilantEye123!' \
  --parameters postgresAdminPassword='VigilantEye123!'
```

#### 3. Get Deployment Outputs
```bash
# Get resource names
POSTGRES_SERVER=$(az deployment group show --resource-group vigilanteye-rg --name arm-template --query properties.outputs.postgresServerName.value -o tsv)
ACR_NAME=$(az deployment group show --resource-group vigilanteye-rg --name arm-template --query properties.outputs.containerRegistryName.value -o tsv)
STORAGE_ACCOUNT=$(az deployment group show --resource-group vigilanteye-rg --name arm-template --query properties.outputs.storageAccountName.value -o tsv)

echo "PostgreSQL Server: $POSTGRES_SERVER"
echo "Container Registry: $ACR_NAME"
echo "Storage Account: $STORAGE_ACCOUNT"
```

#### 4. Build and Push Images
```bash
# Login to ACR
az acr login --name $ACR_NAME

# Build backend image
docker build -t $ACR_NAME.azurecr.io/vigilanteye-backend:latest ./backend
docker push $ACR_NAME.azurecr.io/vigilanteye-backend:latest

# Build frontend image
docker build -t $ACR_NAME.azurecr.io/vigilanteye-frontend:latest ./frontend
docker push $ACR_NAME.azurecr.io/vigilanteye-frontend:latest
```

#### 5. Create Storage Shares
```bash
# Get storage key
STORAGE_KEY=$(az storage account keys list --resource-group vigilanteye-rg --account-name $STORAGE_ACCOUNT --query '[0].value' -o tsv)

# Create shares
az storage share create --name vigilanteye-storage --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY
az storage share create --name vigilanteye-logs --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY
```

#### 6. Deploy Backend Container
```bash
az container create \
  --resource-group vigilanteye-rg \
  --name vigilanteye-backend \
  --image $ACR_NAME.azurecr.io/vigilanteye-backend:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="postgresql://vigilanteye:VigilantEye123!@$POSTGRES_SERVER.postgres.database.azure.com:5432/vigilanteye" \
    CACHE_DIR="/app/storage/local_cache" \
    CACHE_MAX_MEMORY_ITEMS="1000" \
    CACHE_DEFAULT_TTL="3600" \
    CACHE_CLEANUP_INTERVAL="300" \
    SECRET_KEY="VigilantEyeSecretKey123!" \
    JWT_SECRET_KEY="VigilantEyeJWTSecret123!" \
    APP_ENV="production" \
  --azure-file-volume-share-name vigilanteye-storage \
  --azure-file-volume-account-name $STORAGE_ACCOUNT \
  --azure-file-volume-account-key $STORAGE_KEY \
  --azure-file-volume-mount-path /app/storage \
  --registry-login-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --restart-policy Always
```

#### 7. Deploy Frontend Container
```bash
az container create \
  --resource-group vigilanteye-rg \
  --name vigilanteye-frontend \
  --image $ACR_NAME.azurecr.io/vigilanteye-frontend:latest \
  --cpu 0.5 \
  --memory 1 \
  --ports 80 \
  --registry-login-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --restart-policy Always
```

#### 8. Get Container IPs
```bash
BACKEND_IP=$(az container show --resource-group vigilanteye-rg --name vigilanteye-backend --query ipAddress.ip -o tsv)
FRONTEND_IP=$(az container show --resource-group vigilanteye-rg --name vigilanteye-frontend --query ipAddress.ip -o tsv)

echo "Backend URL: http://$BACKEND_IP:8000"
echo "Frontend URL: http://$FRONTEND_IP"
echo "Health Check: http://$BACKEND_IP:8000/api/health"
```

## 🎯 Option 2: Azure Kubernetes Service (AKS)

### Step 1: Create AKS Cluster
```bash
# Create AKS cluster
az aks create \
  --resource-group vigilanteye-rg \
  --name vigilanteye-aks \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group vigilanteye-rg --name vigilanteye-aks
```

### Step 2: Create Kubernetes Secrets
```bash
# Create namespace
kubectl create namespace vigilanteye

# Create secrets
kubectl create secret generic vigilanteye-secrets \
  --from-literal=database-url="postgresql://vigilanteye:VigilantEye123!@$POSTGRES_SERVER.postgres.database.azure.com:5432/vigilanteye" \
  --from-literal=cache-dir="/app/storage/local_cache" \
  --from-literal=secret-key="VigilantEyeSecretKey123!" \
  --from-literal=jwt-secret-key="VigilantEyeJWTSecret123!" \
  --from-literal=openai-api-key="${OPENAI_API_KEY:-}" \
  --from-literal=telegram-bot-token="${TELEGRAM_BOT_TOKEN:-}" \
  --namespace vigilanteye
```

### Step 3: Deploy with Kubernetes
```bash
# Apply Kubernetes manifests
kubectl apply -f azure/kubernetes.yaml

# Check deployment status
kubectl get pods -n vigilanteye
kubectl get services -n vigilanteye
```

### Step 4: Get Service URLs
```bash
# Get external IPs
kubectl get services -n vigilanteye

# Port forward for testing
kubectl port-forward -n vigilanteye service/vigilanteye-backend 8000:8000
kubectl port-forward -n vigilanteye service/vigilanteye-frontend 3000:80
```

## 🔧 Configuration Management

### Environment Variables for Production

```env
# Database
DATABASE_URL=postgresql://vigilanteye:VigilantEye123!@your-postgres-server.postgres.database.azure.com:5432/vigilanteye

# Local Cache
CACHE_DIR=/app/storage/local_cache
CACHE_MAX_MEMORY_ITEMS=1000
CACHE_DEFAULT_TTL=3600
CACHE_CLEANUP_INTERVAL=300

# Security
SECRET_KEY=VigilantEyeSecretKey123!
JWT_SECRET_KEY=VigilantEyeJWTSecret123!

# Application
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

# External APIs
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# AI Configuration
AI_DEVICE=cpu
MODEL_CACHE_ENABLED=true
MODEL_CACHE_PATH=/app/storage/model_cache
```

### Azure Key Vault Integration

```bash
# Create Key Vault
az keyvault create \
  --name vigilanteye-kv \
  --resource-group vigilanteye-rg \
  --location eastus

# Store secrets
az keyvault secret set --vault-name vigilanteye-kv --name database-url --value "your-database-url"
az keyvault secret set --vault-name vigilanteye-kv --name secret-key --value "your-secret-key"
az keyvault secret set --vault-name vigilanteye-kv --name jwt-secret-key --value "your-jwt-secret-key"
```

## 📊 Monitoring & Logging

### Azure Monitor Integration

```bash
# Enable Application Insights
az monitor app-insights component create \
  --app vigilanteye-insights \
  --location eastus \
  --resource-group vigilanteye-rg

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show --app vigilanteye-insights --resource-group vigilanteye-rg --query instrumentationKey -o tsv)
```

### Log Analytics Workspace

```bash
# Create Log Analytics workspace
az monitor log-analytics workspace create \
  --resource-group vigilanteye-rg \
  --workspace-name vigilanteye-logs \
  --location eastus
```

## 🔒 Security Configuration

### Network Security Groups
```bash
# Create NSG for backend
az network nsg create \
  --resource-group vigilanteye-rg \
  --name vigilanteye-backend-nsg

# Allow HTTP traffic
az network nsg rule create \
  --resource-group vigilanteye-rg \
  --nsg-name vigilanteye-backend-nsg \
  --name AllowHTTP \
  --priority 1000 \
  --source-address-prefixes '*' \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 8000 \
  --access Allow \
  --protocol Tcp
```

### SSL/TLS Configuration
```bash
# Create SSL certificate (using Let's Encrypt or Azure Certificate)
# Configure HTTPS in nginx configuration
```

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
az container logs --resource-group vigilanteye-rg --name vigilanteye-backend

# Check container status
az container show --resource-group vigilanteye-rg --name vigilanteye-backend --query instanceView.state
```

#### Database Connection Issues
```bash
# Test database connectivity
az postgres server show --resource-group vigilanteye-rg --name $POSTGRES_SERVER

# Check firewall rules
az postgres server firewall-rule list --resource-group vigilanteye-rg --server-name $POSTGRES_SERVER
```

#### Image Pull Issues
```bash
# Check ACR credentials
az acr credential show --name $ACR_NAME

# Test image pull
docker pull $ACR_NAME.azurecr.io/vigilanteye-backend:latest
```

### Health Checks

```bash
# Check backend health
curl http://$BACKEND_IP:8000/api/health

# Check detailed health
curl http://$BACKEND_IP:8000/api/health/detailed

# Check frontend
curl http://$FRONTEND_IP
```

## 📈 Scaling & Performance

### Auto-scaling (AKS)
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vigilanteye-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vigilanteye-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Performance Optimization
```bash
# Enable Azure CDN for static assets
az cdn profile create \
  --name vigilanteye-cdn \
  --resource-group vigilanteye-rg \
  --sku Standard_Microsoft

# Configure Redis Cache (if needed)
az redis create \
  --resource-group vigilanteye-rg \
  --name vigilanteye-redis \
  --location eastus \
  --sku Standard \
  --vm-size c1
```

## 💰 Cost Optimization

### Resource Sizing
- **Development**: Standard_B1s (1 vCPU, 1 GB RAM)
- **Production**: Standard_D2s_v3 (2 vCPU, 8 GB RAM)
- **High Load**: Standard_D4s_v3 (4 vCPU, 16 GB RAM)

### Cost Management
```bash
# Set up cost alerts
az consumption budget create \
  --budget-name vigilanteye-budget \
  --resource-group vigilanteye-rg \
  --amount 100 \
  --time-grain Monthly
```

## 🔄 CI/CD Pipeline

### GitHub Actions Integration
```yaml
# .github/workflows/azure-deploy.yml
name: Deploy to Azure
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    - name: Deploy to ACI
      run: |
        az container create \
          --resource-group vigilanteye-rg \
          --name vigilanteye-backend \
          --image ${{ secrets.ACR_NAME }}.azurecr.io/vigilanteye-backend:latest
```

## 📋 Maintenance

### Regular Tasks
- **Backup Database**: Daily automated backups
- **Update Images**: Weekly security updates
- **Monitor Costs**: Monthly cost review
- **Security Audit**: Quarterly security assessment

### Backup Strategy
```bash
# Database backup
az postgres server-backup create \
  --resource-group vigilanteye-rg \
  --server-name $POSTGRES_SERVER \
  --backup-name daily-backup-$(date +%Y%m%d)

# Storage backup
az storage blob copy start \
  --source-uri https://$STORAGE_ACCOUNT.blob.core.windows.net/vigilanteye-storage \
  --destination-container backup \
  --destination-blob vigilanteye-storage-$(date +%Y%m%d)
```

## 🎯 Next Steps

1. **Set up monitoring**: Configure Azure Monitor and Application Insights
2. **Implement CI/CD**: Set up automated deployment pipeline
3. **Configure SSL**: Set up HTTPS with SSL certificates
4. **Set up backups**: Implement automated backup strategy
5. **Performance tuning**: Optimize based on usage patterns

## 📞 Support

For Azure-specific issues:
- **Azure Documentation**: https://docs.microsoft.com/en-us/azure/
- **Azure Support**: https://azure.microsoft.com/en-us/support/
- **Community Forums**: https://docs.microsoft.com/en-us/answers/topics/azure.html

---

**Last Updated**: 2024-01-01  
**Version**: 1.0.0
