# VigilantEye Azure Container Deployment Guide

## Issues Fixed

### 1. **Docker Hub Rate Limiting**
   - **Problem**: Docker Hub has rate limits for anonymous pulls
   - **Solution**: Created Azure Container Registry (vigilanteyeacr) and pushed image there

### 2. **SSL Connection Error** 
   - **Problem**: `Connections using insecure transport are prohibited while --require_secure_transport=ON`
   - **Solution**: Added SSL parameters to DATABASE_URL: `?ssl_ca=/etc/ssl/certs/ca-certificates.crt`

### 3. **Localhost Connection Error**
   - **Problem**: Application trying to connect to localhost instead of Azure MySQL
   - **Solution**: URL-encoded the password special characters (`!` → `%21`)

## Deployment Options

### Option 1: Run PowerShell Script (Windows - Recommended)
```powershell
.\deploy.ps1
```

### Option 2: Run Bash Script (Linux/Mac)
```bash
chmod +x deploy.sh
./deploy.sh
```

### Option 3: Manual Deployment Command

#### PowerShell (Windows):
```powershell
# Get ACR password
$acrPassword = az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv

# Delete existing container (if any)
az container delete --resource-group vigilanteye-docker-rg --name vigilanteye-app --yes

# Create new container with correct configuration
az container create `
    --resource-group vigilanteye-docker-rg `
    --name vigilanteye-app `
    --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest `
    --dns-name-label vigilanteye-app `
    --ports 8000 `
    --cpu 1 `
    --memory 2 `
    --os-type Linux `
    --registry-login-server vigilanteyeacr.azurecr.io `
    --registry-username vigilanteyeacr `
    --registry-password $acrPassword `
    --environment-variables `
        FLASK_ENV=production `
        SECRET_KEY=your-secret-key-here `
        JWT_SECRET_KEY=jwt-secret-string `
        DATABASE_URL='mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt'
```

#### Bash (Linux/Mac):
```bash
# Get ACR password
ACR_PASSWORD=$(az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv)

# Delete existing container (if any)
az container delete --resource-group vigilanteye-docker-rg --name vigilanteye-app --yes

# Create new container
az container create \
    --resource-group vigilanteye-docker-rg \
    --name vigilanteye-app \
    --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest \
    --dns-name-label vigilanteye-app \
    --ports 8000 \
    --cpu 1 \
    --memory 2 \
    --os-type Linux \
    --registry-login-server vigilanteyeacr.azurecr.io \
    --registry-username vigilanteyeacr \
    --registry-password ${ACR_PASSWORD} \
    --environment-variables \
        FLASK_ENV=production \
        SECRET_KEY=your-secret-key-here \
        JWT_SECRET_KEY=jwt-secret-string \
        DATABASE_URL='mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt'
```

### Option 4: Use YAML File
```bash
az container create --resource-group vigilanteye-docker-rg --file deploy-container.yaml
```

## Post-Deployment Steps

### 1. Check Container Status
```bash
az container show \
    --resource-group vigilanteye-docker-rg \
    --name vigilanteye-app \
    --query "{FQDN:ipAddress.fqdn, IP:ipAddress.ip, State:instanceView.state}" \
    --output table
```

### 2. View Container Logs
```bash
# View last 50 lines
az container logs --resource-group vigilanteye-docker-rg --name vigilanteye-app --tail 50

# Follow logs in real-time
az container logs --resource-group vigilanteye-docker-rg --name vigilanteye-app --follow
```

### 3. Run Database Migrations
```bash
az container exec \
    --resource-group vigilanteye-docker-rg \
    --name vigilanteye-app \
    --exec-command "flask db upgrade"
```

### 4. Test the Application
```bash
# Get the FQDN
FQDN=$(az container show --resource-group vigilanteye-docker-rg --name vigilanteye-app --query "ipAddress.fqdn" -o tsv)

# Test health endpoint
curl http://${FQDN}:8000/health

# Or in PowerShell:
$fqdn = az container show --resource-group vigilanteye-docker-rg --name vigilanteye-app --query "ipAddress.fqdn" -o tsv
Invoke-WebRequest -Uri "http://${fqdn}:8000/health"
```

## Application URLs

After successful deployment, your application will be available at:
- **FQDN**: `http://vigilanteye-app.eastus.azurecontainer.io:8000`
- **Health Check**: `http://vigilanteye-app.eastus.azurecontainer.io:8000/health`
- **API Base**: `http://vigilanteye-app.eastus.azurecontainer.io:8000/api`

## Troubleshooting

### Container Won't Start
1. Check logs: `az container logs --resource-group vigilanteye-docker-rg --name vigilanteye-app`
2. Check events: `az container show --resource-group vigilanteye-docker-rg --name vigilanteye-app --query "containers[0].instanceView.events"`

### Database Connection Issues
1. Verify SSL is enabled in the connection string
2. Check that password special characters are URL-encoded (`!` → `%21`)
3. Verify Azure MySQL firewall allows Azure services

### Application Not Responding
1. Check container state: `az container show --resource-group vigilanteye-docker-rg --name vigilanteye-app --query "instanceView.state"`
2. Verify port 8000 is open
3. Check if gunicorn is running: `az container exec --resource-group vigilanteye-docker-rg --name vigilanteye-app --exec-command "ps aux"`

## Key Configuration Details

### Database URL Format
```
mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE?ssl_ca=CERT_PATH
```

**Important**: 
- Use `%21` instead of `!` in password
- Include SSL certificate path for Azure MySQL
- Use PyMySQL driver (not mysqlclient)

### Environment Variables
- `FLASK_ENV`: Set to `production`
- `DATABASE_URL`: MySQL connection string with SSL
- `SECRET_KEY`: Flask secret key for sessions
- `JWT_SECRET_KEY`: JWT token signing key

## Cleanup Commands

### Delete Container
```bash
az container delete --resource-group vigilanteye-docker-rg --name vigilanteye-app --yes
```

### Delete Container Group
```bash
az group delete --name vigilanteye-docker-rg --yes
```

## Next Steps

1. Run the deployment script or command
2. Wait 30-60 seconds for container to start
3. Check logs for any errors
4. Run database migrations
5. Test the application endpoints
6. Monitor logs for issues

## Support

If you encounter issues:
1. Check the logs first
2. Verify all environment variables are set correctly  
3. Ensure Azure MySQL firewall rules allow connections
4. Verify the ACR credentials are valid
