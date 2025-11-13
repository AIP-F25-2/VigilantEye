# Azure Redeployment Script with Log Checking
# This script checks logs, rebuilds, and redeploys the application

param(
    [string]$ResourceGroup = "vigilanteye-docker-rg",
    [string]$RegistryName = "vigilanteyeacr",
    [string]$ContainerAppName = "vigilanteye-app",
    [string]$ImageName = "vigilanteye:latest"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Azure Redeployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure login
Write-Host "[0/6] Checking Azure login..." -ForegroundColor Yellow
try {
    $account = az account show 2>$null
    if (-not $account) {
        Write-Host "Not logged in. Please run: az login" -ForegroundColor Red
        exit 1
    }
    Write-Host "Azure login verified!" -ForegroundColor Green
} catch {
    Write-Host "Please login to Azure: az login" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 1: Check current logs
Write-Host "[1/6] Checking current application logs..." -ForegroundColor Yellow
Write-Host "Recent logs:" -ForegroundColor Cyan
az containerapp logs show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --tail 30 `
    --type console
Write-Host ""

# Step 2: Get application URL
Write-Host "[2/6] Getting application URL..." -ForegroundColor Yellow
$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

if ($fqdn) {
    Write-Host "Current URL: https://$fqdn" -ForegroundColor Cyan
} else {
    Write-Host "Could not retrieve URL" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Build Docker image
Write-Host "[3/6] Building Docker image in ACR..." -ForegroundColor Yellow
Write-Host "This may take 10-15 minutes..." -ForegroundColor Yellow
$buildResult = az acr build --registry $RegistryName --image $ImageName --platform linux/amd64 --timeout 3600 .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed! Check the error messages above." -ForegroundColor Red
    exit 1
}
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host ""

# Step 4: Update Container App
Write-Host "[4/6] Updating Container App with new image..." -ForegroundColor Yellow
$imageFullName = "${RegistryName}.azurecr.io/${ImageName}"
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --image $imageFullName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Container App update failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Container App update initiated!" -ForegroundColor Green
Write-Host ""

# Step 5: Wait for Container App to restart
Write-Host "[5/6] Waiting for Container App to restart (60 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60
Write-Host "Container App should be ready now!" -ForegroundColor Green
Write-Host ""

# Step 6: Check new logs and test
Write-Host "[6/6] Checking new logs and application status..." -ForegroundColor Yellow
Write-Host "Recent startup logs:" -ForegroundColor Cyan
az containerapp logs show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --tail 50 `
    --type console

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Redeployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URL: https://$fqdn" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the application: https://$fqdn/health" -ForegroundColor White
Write-Host "2. Check logs: az containerapp logs show --name $ContainerAppName --resource-group $ResourceGroup --follow" -ForegroundColor White
Write-Host "3. Verify migrations ran: Look for 'Database migrations completed successfully' in logs" -ForegroundColor White
Write-Host ""


