# Azure Deployment Checklist

## ⚠️ Authentication Required

Your Azure MFA token has expired. Please authenticate first:

```powershell
az login
```

## 📋 Deployment Steps

### 1. Check Current Logs
```powershell
az containerapp logs show --name vigilanteye-app --resource-group vigilanteye-docker-rg --tail 100 --type console
```

**Look for:**
- Database connection errors
- Migration errors
- Import errors
- Port binding issues

### 2. Rebuild Docker Image
```powershell
az acr build --registry vigilanteyeacr --image vigilanteye:latest --platform linux/amd64 --timeout 3600 .
```

**Expected time:** 10-15 minutes

### 3. Update Container App
```powershell
az containerapp update --name vigilanteye-app --resource-group vigilanteye-docker-rg --image vigilanteyeacr.azurecr.io/vigilanteye:latest
```

### 4. Wait for Restart
```powershell
Start-Sleep -Seconds 60
```

### 5. Check New Logs
```powershell
az containerapp logs show --name vigilanteye-app --resource-group vigilanteye-docker-rg --tail 100 --type console
```

**Verify:**
- ✅ "Database migrations completed successfully"
- ✅ "Application started successfully"
- ✅ No import errors
- ✅ No database connection errors

### 6. Test Application
```powershell
$url = az containerapp show --name vigilanteye-app --resource-group vigilanteye-docker-rg --query "properties.configuration.ingress.fqdn" --output tsv
Write-Host "Application URL: https://$url"
Invoke-RestMethod -Uri "https://$url/health"
```

## 🚀 Quick Deploy Script

After authentication, run:
```powershell
.\redeploy-azure.ps1
```

## 🔍 Common Issues

### Database Connection Error
- Check `DATABASE_URL` environment variable in Container App
- Verify MySQL server is running and accessible
- Check firewall rules

### Migration Errors
- Check logs for specific migration errors
- Verify database schema matches migrations
- Check if migrations ran: Look for "Database migrations completed successfully"

### Import Errors
- Verify all dependencies in `requirements.txt`
- Check Docker build logs for missing packages
- Ensure all Python modules are properly installed

### Port Issues
- Verify container is binding to port 8000
- Check Container App ingress configuration
- Verify target port is set to 8000

## 📞 Get Application URL

```powershell
az containerapp show --name vigilanteye-app --resource-group vigilanteye-docker-rg --query "properties.configuration.ingress.fqdn" --output tsv
```


