# PowerShell script to deploy VigilantEye container to Azure

Write-Host "Starting VigilantEye deployment..." -ForegroundColor Green

# Variables
$resourceGroup = "vigilanteye-docker-rg"
$containerName = "vigilanteye-app"
$acrName = "vigilanteyeacr"
$imageName = "$acrName.azurecr.io/vigilanteye-web:latest"
$dnsLabel = "vigilanteye-app"
$port = 8000

# Get ACR credentials
Write-Host "Getting ACR credentials..." -ForegroundColor Yellow
$acrUsername = $acrName
$acrPassword = az acr credential show --name $acrName --query "passwords[0].value" -o tsv

if (-not $acrPassword) {
    Write-Host "Failed to get ACR password!" -ForegroundColor Red
    exit 1
}

# Delete existing container if it exists
Write-Host "Checking for existing container..." -ForegroundColor Yellow
$existingContainer = az container show --resource-group $resourceGroup --name $containerName 2>$null
if ($existingContainer) {
    Write-Host "Deleting existing container..." -ForegroundColor Yellow
    az container delete --resource-group $resourceGroup --name $containerName --yes
    Start-Sleep -Seconds 5
}

# Database URL with URL-encoded password (! becomes %21)
$databaseUrl = "mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt"

Write-Host "Creating container with secure SSL connection..." -ForegroundColor Yellow

# Create container
az container create `
    --resource-group $resourceGroup `
    --name $containerName `
    --image $imageName `
    --dns-name-label $dnsLabel `
    --ports $port `
    --cpu 1 `
    --memory 2 `
    --os-type Linux `
    --registry-login-server "$acrName.azurecr.io" `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --environment-variables `
        FLASK_ENV=production `
        SECRET_KEY=your-secret-key-here `
        JWT_SECRET_KEY=jwt-secret-string `
        "DATABASE_URL=$databaseUrl"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nContainer created successfully!" -ForegroundColor Green
    
    # Wait for container to start
    Write-Host "`nWaiting for container to start (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Get container details
    Write-Host "`nGetting container details..." -ForegroundColor Yellow
    $fqdn = az container show --resource-group $resourceGroup --name $containerName --query "ipAddress.fqdn" -o tsv
    $ip = az container show --resource-group $resourceGroup --name $containerName --query "ipAddress.ip" -o tsv
    $state = az container show --resource-group $resourceGroup --name $containerName --query "instanceView.state" -o tsv
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Container Name: $containerName"
    Write-Host "State: $state"
    Write-Host "FQDN: $fqdn"
    Write-Host "IP Address: $ip"
    Write-Host "Application URL: http://${fqdn}:${port}" -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # Show logs
    Write-Host "Container logs:" -ForegroundColor Yellow
    az container logs --resource-group $resourceGroup --name $containerName --tail 50
    
    Write-Host "`nTo view real-time logs, run:" -ForegroundColor Cyan
    Write-Host "az container logs --resource-group $resourceGroup --name $containerName --follow" -ForegroundColor White
    
    Write-Host "`nTo test the application, run:" -ForegroundColor Cyan
    Write-Host "curl http://${fqdn}:${port}/health" -ForegroundColor White
    
} else {
    Write-Host "`nContainer creation failed!" -ForegroundColor Red
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    exit 1
}
