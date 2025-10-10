# 🎉 HTTPS Migration Complete!

## ✅ Successfully Migrated to Azure Container Apps

Your VIGILANTEye application now has **automatic HTTPS** with free SSL certificates!

## 🔒 New HTTPS URLs

### Web Application
- **Homepage**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io
- **Login**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/login
- **Register**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/register
- **Dashboard**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/dashboard

### API Endpoints
- **Health**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/health
- **API Register**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/api/auth/register
- **API Login**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/api/auth/login

## 🚀 Performance Improvements

### Resources
- **CPU**: 2 cores
- **Memory**: 4GB
- **Workers**: 4 Gunicorn workers
- **Threads**: 2 per worker (8 concurrent requests)

### Auto-Scaling
- **Min Replicas**: 1
- **Max Replicas**: 3
- **Auto-scales** based on CPU/Memory usage

### Benefits
- ✅ **HTTPS by default** (free SSL certificate)
- ✅ **Auto-scaling** (handles traffic spikes)
- ✅ **Zero-downtime deployments**
- ✅ **Built-in monitoring** (Application Insights)
- ✅ **Better performance** (2x CPU, 2x RAM)
- ✅ **Load balancing** across replicas

## 📊 Before vs After

| Feature | Container Instances | Container Apps |
|---------|-------------------|----------------|
| Protocol | ❌ HTTP only | ✅ HTTPS + HTTP |
| SSL Certificate | ❌ None | ✅ Free & Auto-renewed |
| CPU | 1 core | 2 cores |
| Memory | 2GB | 4GB |
| Auto-scaling | ❌ No | ✅ Yes (1-3 replicas) |
| Load Balancing | ❌ No | ✅ Yes |
| Zero Downtime | ❌ No | ✅ Yes |
| Monitoring | Basic | Advanced (App Insights) |
| Cost | ~$30/month | ~$40-60/month |

## 🎯 Management Commands

### View App Status
```bash
az containerapp show \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --query "{URL:properties.configuration.ingress.fqdn, State:properties.runningStatus}"
```

### View Logs
```bash
az containerapp logs show \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --follow
```

### Update App (New Deployment)
```bash
az containerapp update \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest
```

### Scale App
```bash
# Scale to specific number
az containerapp update \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --min-replicas 2 \
  --max-replicas 5

# Scale based on HTTP requests
az containerapp update \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50
```

### View Revisions
```bash
az containerapp revision list \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --output table
```

### Set Environment Variables
```bash
az containerapp update \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --set-env-vars "NEW_VAR=value"
```

## 🧪 Test Your HTTPS Application

### Test Health Endpoint
```powershell
Invoke-RestMethod -Uri "https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/health"
```

### Test Registration (API)
```powershell
$body = @{
    username = "testuser"
    email = "test@example.com"
    password = "Test123!@#"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/api/auth/register" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

### Open in Browser
```powershell
start https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io
```

## 📈 Monitoring

### Application Insights
Your app is automatically connected to Azure Monitor. View metrics at:
https://portal.azure.com

Navigate to: Resource Groups → vigilanteye-docker-rg → vigilanteye-app → Monitoring

### Available Metrics
- Request count
- Response time
- Failed requests
- CPU usage
- Memory usage
- Active replicas

## 🔄 Continuous Deployment

### Update Process
1. **Make code changes**
2. **Build new image:**
   ```bash
   docker build -t vigilanteyeacr.azurecr.io/vigilanteye-web:latest .
   ```
3. **Push to ACR:**
   ```bash
   az acr login --name vigilanteyeacr
   docker push vigilanteyeacr.azurecr.io/vigilanteye-web:latest
   ```
4. **Update Container App:**
   ```bash
   az containerapp update \
     --resource-group vigilanteye-docker-rg \
     --name vigilanteye-app \
     --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest
   ```

Zero downtime - Container Apps handles rolling updates automatically!

## 💰 Cost Optimization

Current config: ~$40-60/month

To reduce costs:
```bash
# Reduce to 1 CPU, 2GB RAM
az containerapp update \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --cpu 1 \
  --memory 2Gi \
  --min-replicas 0 \
  --max-replicas 2
```

Setting `min-replicas` to 0 enables scale-to-zero (only pay when active).

## 🎯 Next Steps

1. ✅ Test all pages via HTTPS
2. ✅ Update any hardcoded HTTP URLs to HTTPS
3. ✅ Consider custom domain (optional)
4. ✅ Monitor performance metrics
5. ✅ Set up auto-scaling rules

## 🌐 Custom Domain (Optional)

To use your own domain like `app.yourdomain.com`:

1. **Add custom domain:**
```bash
az containerapp hostname add \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --hostname app.yourdomain.com
```

2. **Get verification ID:**
```bash
az containerapp show \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --query properties.customDomainVerificationId
```

3. **Add TXT record** in your DNS:
   - Name: `asuid.app`
   - Value: `[verification-id]`

4. **Add CNAME record:**
   - Name: `app`
   - Value: `vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io`

5. **Bind certificate** (automatic with Container Apps!)

## 📚 Resources

- [Azure Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)
- [Custom Domains](https://learn.microsoft.com/azure/container-apps/custom-domains-managed-certificates)
- [Scaling](https://learn.microsoft.com/azure/container-apps/scale-app)

---

**Migration Date**: October 9, 2025  
**Status**: ✅ HTTPS Enabled & Running  
**URL**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io

