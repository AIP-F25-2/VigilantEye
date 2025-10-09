# Azure Deployment Guide for VigilantEye Flask API

This guide will help you deploy your VigilantEye Flask API to Azure using Azure App Service with MySQL Flexible Server.

## Prerequisites

1. **Azure CLI** installed and configured
2. **Docker** installed locally
3. **Git** repository with your code
4. **Azure subscription** with appropriate permissions

## Quick Start

### Option 1: Automated Deployment (Recommended)

1. **Fork this repository** to your GitHub account
2. **Set up GitHub Secrets**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `AZURE_CREDENTIALS`: Your Azure service principal credentials (JSON format)
     - `MYSQL_ADMIN_PASSWORD`: Strong password for MySQL admin
     - `SECRET_KEY`: Flask secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
     - `JWT_SECRET_KEY`: JWT secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

3. **Update GitHub Actions workflow**:
   - Edit `.github/workflows/azure-deploy.yml`
   - Update the environment variables at the top:
     ```yaml
     env:
       AZURE_WEBAPP_NAME: your-app-name
       AZURE_RESOURCE_GROUP: your-resource-group
       CONTAINER_REGISTRY: your-registry.azurecr.io
     ```

4. **Push to main branch** - GitHub Actions will automatically deploy

### Option 2: Manual Deployment

#### Step 1: Create Azure Resources

**Using PowerShell (Windows):**
```powershell
.\azure-deploy.ps1 -ResourceGroupName "vigilanteye-rg" -AdminEmail "admin@example.com" -MysqlAdminPassword "YourStrongPassword123!" -SecretKey "your-secret-key" -JwtSecretKey "your-jwt-secret-key"
```

**Using Bash (Linux/Mac):**
```bash
./azure-deploy.sh --resource-group vigilanteye-rg --admin-email admin@example.com --mysql-password "YourStrongPassword123!" --secret-key "your-secret-key" --jwt-secret-key "your-jwt-secret-key"
```

#### Step 2: Build and Push Docker Image

```bash
# Build the image
docker build -f Dockerfile.azure -t vigilanteye-api:latest .

# Tag for Azure Container Registry (replace with your registry)
docker tag vigilanteye-api:latest your-registry.azurecr.io/vigilanteye-api:latest

# Push to registry
docker push your-registry.azurecr.io/vigilanteye-api:latest
```

#### Step 3: Update App Service Settings

1. Go to Azure Portal → App Services → Your App
2. Go to Configuration → Application settings
3. Update `DOCKER_CUSTOM_IMAGE_NAME` to your image name
4. Add database connection string:
   ```
   DATABASE_URL=mysql+pymysql://mysqladmin:YourPassword@your-mysql-server.mysql.database.azure.com:3306/flaskapi
   ```

#### Step 4: Run Database Migrations

```bash
# Connect to App Service
az webapp ssh --name your-app-name --resource-group your-resource-group

# Run migrations
flask db upgrade
```

## Architecture

The deployment creates the following Azure resources:

- **App Service Plan**: Basic B1 tier for hosting the Flask application
- **App Service**: Linux-based containerized app service
- **MySQL Flexible Server**: Managed MySQL database
- **Application Insights**: Monitoring and logging
- **Log Analytics Workspace**: Centralized logging

## Configuration

### Environment Variables

The following environment variables are automatically configured:

- `DATABASE_URL`: MySQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `FLASK_ENV`: Set to production
- `WEBSITES_PORT`: Set to 5000

### Database Configuration

- **MySQL Version**: 8.0.21
- **Storage**: 20GB (configurable)
- **Backup**: 7 days retention
- **High Availability**: Disabled (can be enabled for production)

## Monitoring

### Application Insights

- **Performance monitoring**: Track request times and dependencies
- **Error tracking**: Automatic exception logging
- **Custom metrics**: Application-specific metrics
- **Logs**: Centralized logging with Log Analytics

### Health Checks

- **Endpoint**: `/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## Scaling

### Vertical Scaling

Update the App Service Plan SKU in the Bicep template:
```bicep
sku: {
  name: 'P1V2'  // Change from B1 to P1V2 for production
  tier: 'PremiumV2'
  size: 'P1V2'
  family: 'P'
  capacity: 1
}
```

### Horizontal Scaling

Enable auto-scaling in Azure Portal:
1. Go to App Service → Scale out (App Service Plan)
2. Configure auto-scaling rules
3. Set minimum and maximum instances

## Security

### Network Security

- **HTTPS Only**: Enabled by default
- **Firewall Rules**: MySQL server allows Azure services only
- **Private Endpoints**: Can be configured for production

### Authentication

- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: bcrypt for password security
- **CORS**: Configured for cross-origin requests

## Troubleshooting

### Common Issues

1. **Container won't start**:
   - Check Docker image name in App Service settings
   - Verify all environment variables are set
   - Check application logs in Azure Portal

2. **Database connection failed**:
   - Verify MySQL server is running
   - Check firewall rules
   - Validate connection string

3. **Migration errors**:
   - Connect to App Service via SSH
   - Run `flask db upgrade` manually
   - Check database permissions

### Logs

View logs in Azure Portal:
1. Go to App Service → Monitoring → Log stream
2. Or use Azure CLI: `az webapp log tail --name your-app-name --resource-group your-resource-group`

## Cost Optimization

### Development Environment

- Use Basic B1 tier for App Service Plan
- Use Burstable B1ms for MySQL
- Disable Application Insights if not needed

### Production Environment

- Use Premium tiers for better performance
- Enable auto-scaling
- Configure backup retention policies
- Monitor costs with Azure Cost Management

## API Endpoints

After deployment, your API will be available at:
- **Base URL**: `https://your-app-name.azurewebsites.net`
- **Health Check**: `https://your-app-name.azurewebsites.net/health`
- **Authentication**: `https://your-app-name.azurewebsites.net/api/auth/`
- **API v1**: `https://your-app-name.azurewebsites.net/api/`
- **API v2**: `https://your-app-name.azurewebsites.net/api/v2/`

## Support

For issues and questions:
1. Check Azure Portal logs and metrics
2. Review GitHub Actions workflow logs
3. Check application logs in App Service
4. Verify database connectivity and migrations
