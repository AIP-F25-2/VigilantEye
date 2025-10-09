#!/bin/bash
# Bash script to deploy VigilantEye container to Azure

set -e

echo "Starting VigilantEye deployment..."

# Variables
RESOURCE_GROUP="vigilanteye-docker-rg"
CONTAINER_NAME="vigilanteye-app"
ACR_NAME="vigilanteyeacr"
IMAGE_NAME="${ACR_NAME}.azurecr.io/vigilanteye-web:latest"
DNS_LABEL="vigilanteye-app"
PORT=8000

# Get ACR credentials
echo "Getting ACR credentials..."
ACR_USERNAME="${ACR_NAME}"
ACR_PASSWORD=$(az acr credential show --name ${ACR_NAME} --query "passwords[0].value" -o tsv)

if [ -z "$ACR_PASSWORD" ]; then
    echo "Failed to get ACR password!"
    exit 1
fi

# Delete existing container if it exists
echo "Checking for existing container..."
if az container show --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} &>/dev/null; then
    echo "Deleting existing container..."
    az container delete --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --yes
    sleep 5
fi

# Database URL with URL-encoded password (! becomes %21)
DATABASE_URL="mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt"

echo "Creating container with secure SSL connection..."

# Create container
az container create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${CONTAINER_NAME} \
    --image ${IMAGE_NAME} \
    --dns-name-label ${DNS_LABEL} \
    --ports ${PORT} \
    --cpu 1 \
    --memory 2 \
    --os-type Linux \
    --registry-login-server "${ACR_NAME}.azurecr.io" \
    --registry-username ${ACR_USERNAME} \
    --registry-password ${ACR_PASSWORD} \
    --environment-variables \
        FLASK_ENV=production \
        SECRET_KEY=your-secret-key-here \
        JWT_SECRET_KEY=jwt-secret-string \
        DATABASE_URL="${DATABASE_URL}"

if [ $? -eq 0 ]; then
    echo ""
    echo "Container created successfully!"
    
    # Wait for container to start
    echo ""
    echo "Waiting for container to start (30 seconds)..."
    sleep 30
    
    # Get container details
    echo "Getting container details..."
    FQDN=$(az container show --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --query "ipAddress.fqdn" -o tsv)
    IP=$(az container show --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --query "ipAddress.ip" -o tsv)
    STATE=$(az container show --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --query "instanceView.state" -o tsv)
    
    echo ""
    echo "========================================"
    echo "Deployment Complete!"
    echo "========================================"
    echo "Container Name: ${CONTAINER_NAME}"
    echo "State: ${STATE}"
    echo "FQDN: ${FQDN}"
    echo "IP Address: ${IP}"
    echo "Application URL: http://${FQDN}:${PORT}"
    echo "========================================"
    echo ""
    
    # Show logs
    echo "Container logs:"
    az container logs --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --tail 50
    
    echo ""
    echo "To view real-time logs, run:"
    echo "az container logs --resource-group ${RESOURCE_GROUP} --name ${CONTAINER_NAME} --follow"
    
    echo ""
    echo "To test the application, run:"
    echo "curl http://${FQDN}:${PORT}/health"
    
else
    echo ""
    echo "Container creation failed!"
    echo "Please check the error messages above."
    exit 1
fi
