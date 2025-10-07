# Azure Deployment Script for VigilantEye Flask API
param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "East US",
    
    [Parameter(Mandatory=$false)]
    [string]$AppName = "vigilanteye-api",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "prod",
    
    [Parameter(Mandatory=$true)]
    [string]$AdminEmail,
    
    [Parameter(Mandatory=$true)]
    [string]$MysqlAdminPassword,
    
    [Parameter(Mandatory=$true)]
    [string]$SecretKey,
    
    [Parameter(Mandatory=$true)]
    [string]$JwtSecretKey
)

Write-Host "Starting Azure deployment for VigilantEye Flask API..." -ForegroundColor Green

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if logged in to Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Please log in to Azure CLI first:" -ForegroundColor Yellow
    az login
}

# Create resource group if it doesn't exist
Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

# Deploy Bicep template
Write-Host "Deploying Azure resources..." -ForegroundColor Yellow
$deploymentResult = az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file azure-resources.bicep `
    --parameters `
        appName=$AppName `
        environment=$Environment `
        adminEmail=$AdminEmail `
        mysqlAdminPassword=$MysqlAdminPassword `
        secretKey=$SecretKey `
        jwtSecretKey=$JwtSecretKey `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed!"
    exit 1
}

# Get deployment outputs
$appServiceName = $deploymentResult.properties.outputs.appServiceName.value
$appServiceUrl = $deploymentResult.properties.outputs.appServiceUrl.value
$mysqlServerName = $deploymentResult.properties.outputs.mysqlServerName.value

Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "App Service Name: $appServiceName" -ForegroundColor Cyan
Write-Host "App Service URL: $appServiceUrl" -ForegroundColor Cyan
Write-Host "MySQL Server: $mysqlServerName" -ForegroundColor Cyan

# Instructions for next steps
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Build and push your Docker image to Azure Container Registry or Docker Hub" -ForegroundColor White
Write-Host "2. Update the DOCKER_CUSTOM_IMAGE_NAME in App Service settings" -ForegroundColor White
Write-Host "3. Run database migrations:" -ForegroundColor White
Write-Host "   az webapp ssh --name $appServiceName --resource-group $ResourceGroupName" -ForegroundColor Gray
Write-Host "   flask db upgrade" -ForegroundColor Gray
Write-Host "4. Test your API at: $appServiceUrl" -ForegroundColor White
