# Setup GitHub Secrets for CI/CD Pipeline
# Requires GitHub CLI (gh) to be installed

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Secrets Setup for VIGILANTEye" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if gh CLI is installed
Write-Host "Checking GitHub CLI..." -ForegroundColor Yellow
gh --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ GitHub CLI not found!" -ForegroundColor Red
    Write-Host "Install from: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ GitHub CLI available`n" -ForegroundColor Green

# Check if authenticated
Write-Host "Checking GitHub authentication..." -ForegroundColor Yellow
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to GitHub:" -ForegroundColor Yellow
    gh auth login
}
Write-Host ""

# Get Azure credentials
Write-Host "Fetching Azure credentials..." -ForegroundColor Yellow

$acrPassword = az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv
Write-Host "✅ Got ACR password" -ForegroundColor Green

# Create service principal
Write-Host "`nCreating Azure Service Principal..." -ForegroundColor Yellow
$azureCredentials = az ad sp create-for-rbac `
  --name "vigilanteye-github-actions" `
  --role contributor `
  --scopes "/subscriptions/0d5e1028-f327-4038-b255-9d4ef2f80895/resourceGroups/vigilanteye-docker-rg" `
  --sdk-auth

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service Principal created" -ForegroundColor Green
} else {
    Write-Host "⚠️ Service Principal may already exist" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setting GitHub Secrets..." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Set secrets
Write-Host "Setting ACR secrets..." -ForegroundColor Yellow
gh secret set ACR_NAME --body "vigilanteyeacr"
gh secret set ACR_LOGIN_SERVER --body "vigilanteyeacr.azurecr.io"
gh secret set ACR_USERNAME --body "vigilanteyeacr"
gh secret set ACR_PASSWORD --body $acrPassword

Write-Host "Setting Azure credentials..." -ForegroundColor Yellow
$azureCredentials | gh secret set AZURE_CREDENTIALS

Write-Host "Setting application secrets..." -ForegroundColor Yellow
gh secret set SECRET_KEY --body "your-secret-key-here-change-in-production"
gh secret set JWT_SECRET_KEY --body "jwt-secret-string-change-in-production"
gh secret set DATABASE_URL --body "mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt"

Write-Host "Setting Airflow secrets..." -ForegroundColor Yellow
gh secret set AIRFLOW_URL --body "http://localhost:8080"
gh secret set AIRFLOW_USERNAME --body "admin"
gh secret set AIRFLOW_PASSWORD --body "admin123"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ All Secrets Configured!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Verify secrets:" -ForegroundColor Yellow
gh secret list

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Push code to GitHub" -ForegroundColor White
Write-Host "2. Create a PR to test CI/CD" -ForegroundColor White
Write-Host "3. Merge to main for production deployment" -ForegroundColor White
Write-Host "4. Start Airflow: .\start-airflow.ps1`n" -ForegroundColor White
