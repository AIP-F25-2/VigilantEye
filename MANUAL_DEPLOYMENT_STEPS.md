# Manual Deployment Steps for VIGILANTEye

## Prerequisites
- Azure CLI installed and logged in
- Resource Group: `vigilanteye-docker-rg`
- Container App: `vigilanteye-app`
- Container Registry: `vigilanteyeacr`

## Step 1: Check Build Status

Wait for the Docker build to complete. Check status with:

```powershell
az acr task list-runs --registry vigilanteyeacr --output table --top 1
```

Wait until STATUS shows "Succeeded" (not "Running").

## Step 2: Update Container App

Once the build is complete, update the Container App with the new image:

```powershell
az containerapp update `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --image vigilanteyeacr.azurecr.io/vigilanteye:latest
```

## Step 3: Wait for Container App to Restart

Wait about 30-60 seconds for the Container App to pull the new image and restart:

```powershell
Start-Sleep -Seconds 60
```

## Step 4: Get Application URL

Get your application URL:

```powershell
az containerapp show `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv
```

## Step 5: Run Database Migrations

Run the database migrations to create the FaceAi tables:

```powershell
az containerapp exec `
    --name vigilanteye-app `
    --resource-group vigilanteye-docker-rg `
    --command "flask db upgrade"
```

## Step 6: Verify Deployment

Test the application:

1. Health check:
   ```powershell
   $url = az containerapp show --name vigilanteye-app --resource-group vigilanteye-docker-rg --query "properties.configuration.ingress.fqdn" --output tsv
   Invoke-RestMethod -Uri "https://$url/health" -Method GET
   ```

2. Check logs if needed:
   ```powershell
   az containerapp logs show `
       --name vigilanteye-app `
       --resource-group vigilanteye-docker-rg `
       --follow
   ```

## Troubleshooting

If the Container App fails to start:
1. Check logs: `az containerapp logs show --name vigilanteye-app --resource-group vigilanteye-docker-rg --follow`
2. Verify environment variables are set correctly
3. Check database connectivity

If migrations fail:
1. Ensure database credentials are correct in Container App environment variables
2. Check database connection: `az containerapp exec --name vigilanteye-app --resource-group vigilanteye-docker-rg --command "flask db current"`

