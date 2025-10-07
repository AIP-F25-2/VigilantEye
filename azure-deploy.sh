#!/bin/bash
# Azure Deployment Script for VigilantEye Flask API

set -e

# Default values
RESOURCE_GROUP_NAME=""
LOCATION="East US"
APP_NAME="vigilanteye-api"
ENVIRONMENT="prod"
ADMIN_EMAIL=""
MYSQL_ADMIN_PASSWORD=""
SECRET_KEY=""
JWT_SECRET_KEY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group)
            RESOURCE_GROUP_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --app-name)
            APP_NAME="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --admin-email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        --mysql-password)
            MYSQL_ADMIN_PASSWORD="$2"
            shift 2
            ;;
        --secret-key)
            SECRET_KEY="$2"
            shift 2
            ;;
        --jwt-secret-key)
            JWT_SECRET_KEY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --resource-group <name> --admin-email <email> --mysql-password <password> --secret-key <key> --jwt-secret-key <key> [options]"
            echo ""
            echo "Required:"
            echo "  --resource-group     Azure resource group name"
            echo "  --admin-email        Admin email address"
            echo "  --mysql-password     MySQL admin password"
            echo "  --secret-key         Flask secret key"
            echo "  --jwt-secret-key     JWT secret key"
            echo ""
            echo "Optional:"
            echo "  --location          Azure location (default: East US)"
            echo "  --app-name          Application name (default: vigilanteye-api)"
            echo "  --environment       Environment (default: prod)"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$RESOURCE_GROUP_NAME" || -z "$ADMIN_EMAIL" || -z "$MYSQL_ADMIN_PASSWORD" || -z "$SECRET_KEY" || -z "$JWT_SECRET_KEY" ]]; then
    echo "Error: Missing required parameters"
    echo "Use --help for usage information"
    exit 1
fi

echo "Starting Azure deployment for VigilantEye Flask API..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "Please log in to Azure CLI first:"
    az login
fi

# Create resource group if it doesn't exist
echo "Creating resource group: $RESOURCE_GROUP_NAME"
az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION"

# Deploy Bicep template
echo "Deploying Azure resources..."
DEPLOYMENT_RESULT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --template-file azure-resources.bicep \
    --parameters \
        appName="$APP_NAME" \
        environment="$ENVIRONMENT" \
        adminEmail="$ADMIN_EMAIL" \
        mysqlAdminPassword="$MYSQL_ADMIN_PASSWORD" \
        secretKey="$SECRET_KEY" \
        jwtSecretKey="$JWT_SECRET_KEY" \
    --output json)

# Extract outputs
APP_SERVICE_NAME=$(echo "$DEPLOYMENT_RESULT" | jq -r '.properties.outputs.appServiceName.value')
APP_SERVICE_URL=$(echo "$DEPLOYMENT_RESULT" | jq -r '.properties.outputs.appServiceUrl.value')
MYSQL_SERVER_NAME=$(echo "$DEPLOYMENT_RESULT" | jq -r '.properties.outputs.mysqlServerName.value')

echo "Deployment completed successfully!"
echo "App Service Name: $APP_SERVICE_NAME"
echo "App Service URL: $APP_SERVICE_URL"
echo "MySQL Server: $MYSQL_SERVER_NAME"

# Instructions for next steps
echo ""
echo "Next steps:"
echo "1. Build and push your Docker image to Azure Container Registry or Docker Hub"
echo "2. Update the DOCKER_CUSTOM_IMAGE_NAME in App Service settings"
echo "3. Run database migrations:"
echo "   az webapp ssh --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME"
echo "   flask db upgrade"
echo "4. Test your API at: $APP_SERVICE_URL"
