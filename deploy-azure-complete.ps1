# Complete Azure Deployment Script
# Monitors build and completes deployment

param(
    [string]$ResourceGroup = "vigilanteye-docker-rg",
    [string]$RegistryName = "vigilanteyeacr",
    [string]$ContainerAppName = "vigilanteye-app",
    [string]$ImageName = "vigilanteye:latest"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "VIGILANTEye Azure Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Monitor build status
Write-Host "[1/5] Monitoring ACR build status..." -ForegroundColor Yellow
$maxWait = 20  # Wait up to 20 minutes
$waited = 0
$buildStatus = ""

while ($buildStatus -ne "Succeeded" -and $waited -lt $maxWait) {
    $waited++
    Write-Host "Checking build status... (Attempt $waited/$maxWait)" -ForegroundColor Gray
    
    $runInfo = az acr task list-runs --registry $RegistryName --output json --query "[0]" 2>$null | ConvertFrom-Json
    
    if ($runInfo) {
        $status = $runInfo.status
        $runId = $runInfo.runId
        
        if ($status -eq "Succeeded") {
            $buildStatus = "Succeeded"
            Write-Host "✅ Build '$runId' completed successfully!" -ForegroundColor Green
            break
        } elseif ($status -eq "Failed") {
            Write-Host "❌ Build '$runId' failed!" -ForegroundColor Red
            Write-Host "Check ACR logs for details." -ForegroundColor Yellow
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
    Write-Host "⚠️ Build did not complete within time limit. Proceeding anyway..." -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Update Container App
Write-Host "[2/5] Updating Container App with new image..." -ForegroundColor Yellow
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
Write-Host "[3/5] Waiting for Container App to restart (90 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 90
Write-Host "✅ Container App should be ready!" -ForegroundColor Green
Write-Host ""

# Step 4: Get application URL
Write-Host "[4/5] Getting application URL..." -ForegroundColor Yellow
$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

if ($fqdn) {
    Write-Host "✅ Application URL: https://$fqdn" -ForegroundColor Green
} else {
    Write-Host "⚠️ Could not retrieve application URL" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Check logs and test
Write-Host "[5/5] Checking application logs..." -ForegroundColor Yellow
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
Write-Host "Application URL: https://$fqdn" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Test endpoints:" -ForegroundColor Green
Write-Host "   • Health: https://$fqdn/health" -ForegroundColor White
Write-Host "   • Login: https://$fqdn/login" -ForegroundColor White
Write-Host "   • Dashboard: https://$fqdn/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Test the application endpoints" -ForegroundColor White
Write-Host "   2. Verify migrations ran (check logs)" -ForegroundColor White
Write-Host "   3. Test login functionality" -ForegroundColor White
Write-Host ""


