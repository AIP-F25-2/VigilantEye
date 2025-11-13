# Complete Deployment Script
# Monitors build and completes deployment

param(
    [string]$ResourceGroup = "vigilanteye-docker-rg",
    [string]$RegistryName = "vigilanteyeacr",
    [string]$ContainerAppName = "vigilanteye-app",
    [string]$ImageName = "vigilanteye:latest"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Completing VIGILANTEye Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check build status
Write-Host "[1/4] Checking ACR build status..." -ForegroundColor Yellow
$maxAttempts = 60  # Check for 60 minutes
$attempt = 0
$buildStatus = ""

while ($buildStatus -ne "Succeeded" -and $attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "Attempt $attempt: Checking build status..." -ForegroundColor Gray
    $runInfo = az acr task list-runs --registry $RegistryName --output json --query "[0]" 2>$null | ConvertFrom-Json
    
    if ($runInfo) {
        $status = $runInfo.status
        $runId = $runInfo.runId
        
        if ($status -eq "Succeeded") {
            $buildStatus = "Succeeded"
            Write-Host "✅ ACR build '$runId' completed successfully!" -ForegroundColor Green
        } elseif ($status -eq "Failed") {
            Write-Host "❌ ACR build '$runId' failed. Check ACR logs." -ForegroundColor Red
            exit 1
        } else {
            Write-Host "Build '$runId' status: $status. Waiting 60 seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds 60
        }
    } else {
        Write-Host "Waiting for build to start... (60 seconds)" -ForegroundColor Yellow
        Start-Sleep -Seconds 60
    }
}

if ($buildStatus -ne "Succeeded") {
    Write-Host "❌ Build did not complete within the time limit." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Update Container App
Write-Host "[2/4] Updating Container App with new image..." -ForegroundColor Yellow
$imageFullName = "${RegistryName}.azurecr.io/${ImageName}"
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --image $imageFullName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Container App update failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Container App update initiated!" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for restart
Write-Host "[3/4] Waiting for Container App to restart (90 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 90
Write-Host "✅ Container App should be ready!" -ForegroundColor Green
Write-Host ""

# Step 4: Check logs and verify
Write-Host "[4/4] Checking application logs..." -ForegroundColor Yellow
Write-Host "Recent logs:" -ForegroundColor Cyan
az containerapp logs show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --tail 50 `
    --type console

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

Write-Host "Application URL: https://$fqdn" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Verify the application is working:" -ForegroundColor Green
Write-Host "   https://$fqdn/health" -ForegroundColor White
Write-Host ""


