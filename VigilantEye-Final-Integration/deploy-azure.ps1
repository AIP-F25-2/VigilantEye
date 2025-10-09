# Quick Azure Deployment Script for VigilantEye
param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "East US"
)

Write-Host "🚀 VigilantEye Azure Deployment Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Generate secure keys
$SecretKey = -join ((1..32) | ForEach {Get-Random -InputObject @('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9')})
$JwtSecretKey = -join ((1..32) | ForEach {Get-Random -InputObject @('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9')})
$MysqlPassword = -join ((1..16) | ForEach {Get-Random -InputObject @('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','0','1','2','3','4','5','6','7','8','9')}) + "!"

Write-Host "Generated secure keys:" -ForegroundColor Yellow
Write-Host "Secret Key: $SecretKey" -ForegroundColor Cyan
Write-Host "JWT Secret: $JwtSecretKey" -ForegroundColor Cyan
Write-Host "MySQL Password: $MysqlPassword" -ForegroundColor Cyan
Write-Host ""

# Deploy using the main script
Write-Host "Deploying to Azure..." -ForegroundColor Yellow
& .\azure-deploy.ps1 -ResourceGroupName $ResourceGroupName -Location $Location -AdminEmail "admin@vigilanteye.com" -MysqlAdminPassword $MysqlPassword -SecretKey $SecretKey -JwtSecretKey $JwtSecretKey

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Build and push your Docker image" -ForegroundColor White
Write-Host "2. Update App Service settings with your image name" -ForegroundColor White
Write-Host "3. Run database migrations" -ForegroundColor White
Write-Host "4. Test your API endpoints" -ForegroundColor White
