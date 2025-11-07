#!/bin/bash

# VigilantEye Azure Deployment Script
# This script deploys the VigilantEye application to Azure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="vigilanteye-rg"
LOCATION="eastus"
APP_NAME="vigilanteye"
ENVIRONMENT="production"

echo -e "${BLUE}🚀 Starting VigilantEye Azure Deployment${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

# Login to Azure
echo -e "${YELLOW}🔐 Logging into Azure...${NC}"
az login

# Create resource group
echo -e "${YELLOW}📦 Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy ARM template
echo -e "${YELLOW}🏗️ Deploying Azure resources...${NC}"
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file azure/arm-template.json \
    --parameters appName=$APP_NAME environment=$ENVIRONMENT location=$LOCATION \
    --parameters adminUsername=vigilanteye adminPassword='VigilantEye123!' \
    --parameters postgresAdminPassword='VigilantEye123!' \
    --output table

# Get deployment outputs
echo -e "${YELLOW}📋 Getting deployment outputs...${NC}"
VM_PUBLIC_IP=$(az deployment group show --resource-group $RESOURCE_GROUP --name arm-template --query properties.outputs.vmPublicIP.value -o tsv)
POSTGRES_SERVER=$(az deployment group show --resource-group $RESOURCE_GROUP --name arm-template --query properties.outputs.mysqlServerName.value -o tsv)
ACR_NAME=$(az deployment group show --resource-group $RESOURCE_GROUP --name arm-template --query properties.outputs.containerRegistryName.value -o tsv)
STORAGE_ACCOUNT=$(az deployment group show --resource-group $RESOURCE_GROUP --name arm-template --query properties.outputs.storageAccountName.value -o tsv)

echo -e "${GREEN}✅ Azure resources created successfully!${NC}"
echo -e "${BLUE}VM Public IP: $VM_PUBLIC_IP${NC}"
echo -e "${BLUE}MySQL Server: $POSTGRES_SERVER${NC}"
echo -e "${BLUE}Container Registry: $ACR_NAME${NC}"
echo -e "${BLUE}Storage Account: $STORAGE_ACCOUNT${NC}"

# Login to ACR
echo -e "${YELLOW}🐳 Logging into Azure Container Registry...${NC}"
az acr login --name $ACR_NAME

# Build and push Docker images
echo -e "${YELLOW}🔨 Building and pushing Docker images...${NC}"

# Build backend image
echo -e "${YELLOW}Building backend image...${NC}"
docker build -t $ACR_NAME.azurecr.io/vigilanteye-backend:latest ./backend
docker push $ACR_NAME.azurecr.io/vigilanteye-backend:latest

# Build frontend image
echo -e "${YELLOW}Building frontend image...${NC}"
docker build -t $ACR_NAME.azurecr.io/vigilanteye-frontend:latest ./frontend
docker push $ACR_NAME.azurecr.io/vigilanteye-frontend:latest

# Create storage shares
echo -e "${YELLOW}💾 Creating storage shares...${NC}"
STORAGE_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT --query '[0].value' -o tsv)

az storage share create --name vigilanteye-storage --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY
az storage share create --name vigilanteye-logs --account-name $STORAGE_ACCOUNT --account-key $STORAGE_KEY

# Deploy to Container Instances
echo -e "${YELLOW}🚀 Deploying to Azure Container Instances...${NC}"

# Create environment file for deployment
cat > .env.azure << EOF
DATABASE_URL=mysql+pymysql://vigilanteye:VigilantEye123!@$POSTGRES_SERVER.mysql.database.azure.com:3306/vigilanteye
CACHE_DIR=/app/storage/local_cache
CACHE_MAX_MEMORY_ITEMS=1000
CACHE_DEFAULT_TTL=3600
CACHE_CLEANUP_INTERVAL=300
SECRET_KEY=VigilantEyeSecretKey123!
JWT_SECRET_KEY=VigilantEyeJWTSecret123!
OPENAI_API_KEY=${OPENAI_API_KEY:-}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
STORAGE_ACCOUNT_KEY=$STORAGE_KEY
EOF

# Deploy backend
az container create \
    --resource-group $RESOURCE_GROUP \
    --name vigilanteye-backend \
    --image $ACR_NAME.azurecr.io/vigilanteye-backend:latest \
    --cpu 2 \
    --memory 4 \
    --ports 8000 \
    --environment-variables @.env.azure \
    --azure-file-volume-share-name vigilanteye-storage \
    --azure-file-volume-account-name $STORAGE_ACCOUNT \
    --azure-file-volume-account-key $STORAGE_KEY \
    --azure-file-volume-mount-path /app/storage \
    --registry-login-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
    --restart-policy Always

# Deploy frontend
az container create \
    --resource-group $RESOURCE_GROUP \
    --name vigilanteye-frontend \
    --image $ACR_NAME.azurecr.io/vigilanteye-frontend:latest \
    --cpu 0.5 \
    --memory 1 \
    --ports 80 \
    --registry-login-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
    --restart-policy Always

# Get container IPs
BACKEND_IP=$(az container show --resource-group $RESOURCE_GROUP --name vigilanteye-backend --query ipAddress.ip -o tsv)
FRONTEND_IP=$(az container show --resource-group $RESOURCE_GROUP --name vigilanteye-frontend --query ipAddress.ip -o tsv)

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}Backend URL: http://$BACKEND_IP:8000${NC}"
echo -e "${BLUE}Frontend URL: http://$FRONTEND_IP${NC}"
echo -e "${BLUE}Health Check: http://$BACKEND_IP:8000/api/health${NC}"

# Clean up
rm -f .env.azure

echo -e "${GREEN}✨ VigilantEye is now running on Azure!${NC}"
