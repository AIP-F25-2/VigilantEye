# Manual Deployment Script for VIGILANTEye
# This script provides step-by-step manual deployment instructions

Write-Host "📋 VIGILANTEye Manual Deployment Guide" -ForegroundColor Cyan
Write-Host "=" * 60

# Check prerequisites
Write-Host "`n🔍 Checking Prerequisites..." -ForegroundColor Yellow

$prerequisites = @(
    @{Name="Docker"; Command="docker --version"},
    @{Name="Azure CLI"; Command="az --version"},
    @{Name="Python"; Command="python --version"}
)

foreach ($prereq in $prerequisites) {
    try {
        $output = Invoke-Expression $prereq.Command 2>&1
        Write-Host "  ✅ $($prereq.Name) installed" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $($prereq.Name) not found. Please install it first." -ForegroundColor Red
    }
}

Write-Host "`n📝 Manual Deployment Steps:" -ForegroundColor Yellow
Write-Host "=" * 60

Write-Host "`n1️⃣  Environment Setup" -ForegroundColor Cyan
Write-Host "   - Set environment variables:"
Write-Host "     * DATABASE_URL"
Write-Host "     * SECRET_KEY"
Write-Host "     * JWT_SECRET_KEY"
Write-Host "     * TELEGRAM_BOT_TOKEN"
Write-Host "     * TELEGRAM_WEBHOOK_SECRET"

Write-Host "`n2️⃣  Database Setup" -ForegroundColor Cyan
Write-Host "   - Create MySQL database"
Write-Host "   - Run migrations: flask db upgrade"
Write-Host "   - Verify database connection"

Write-Host "`n3️⃣  Build Docker Image" -ForegroundColor Cyan
Write-Host "   docker build -t vigilanteye:latest ."

Write-Host "`n4️⃣  Test Locally" -ForegroundColor Cyan
Write-Host "   docker-compose up -d"
Write-Host "   # Or: python run.py"

Write-Host "`n5️⃣  Azure Container Registry" -ForegroundColor Cyan
Write-Host "   az acr login --name vigilanteyeacr"
Write-Host "   docker tag vigilanteye:latest vigilanteyeacr.azurecr.io/vigilanteye-web:latest"
Write-Host "   docker push vigilanteyeacr.azurecr.io/vigilanteye-web:latest"

Write-Host "`n6️⃣  Deploy to Azure Container Apps" -ForegroundColor Cyan
Write-Host "   az containerapp update \"
Write-Host "     --name vigilanteye-app \"
Write-Host "     --resource-group vigilanteye-docker-rg \"
Write-Host "     --image vigilanteyeacr.azurecr.io/vigilanteye-web:latest"

Write-Host "`n7️⃣  Configure Environment Variables" -ForegroundColor Cyan
Write-Host "   az containerapp update \"
Write-Host "     --name vigilanteye-app \"
Write-Host "     --resource-group vigilanteye-docker-rg \"
Write-Host "     --set-env-vars KEY=VALUE"

Write-Host "`n8️⃣  Run Database Migrations" -ForegroundColor Cyan
Write-Host "   az containerapp exec \"
Write-Host "     --name vigilanteye-app \"
Write-Host "     --resource-group vigilanteye-docker-rg \"
Write-Host "     --command 'flask db upgrade'"

Write-Host "`n9️⃣  Verify Deployment" -ForegroundColor Cyan
Write-Host "   - Check health endpoint: https://your-app.azurecontainerapps.io/health"
Write-Host "   - Test login/registration"
Write-Host "   - Verify Telegram integration"

Write-Host "`n🔟  Monitoring" -ForegroundColor Cyan
Write-Host "   az containerapp logs show \"
Write-Host "     --name vigilanteye-app \"
Write-Host "     --resource-group vigilanteye-docker-rg \"
Write-Host "     --follow"

Write-Host "`n📚 Additional Resources:" -ForegroundColor Yellow
Write-Host "   - README.md - Full documentation"
Write-Host "   - PROJECT_SUMMARY.md - Project overview"
Write-Host "   - FACEAI_INTEGRATION_GUIDE.md - FaceAI setup"
Write-Host "   - deploy-azure.ps1 - Automated deployment script"

Write-Host "`n✅ Manual deployment guide displayed!" -ForegroundColor Green
Write-Host "   Use 'deploy-azure.ps1' for automated deployment." -ForegroundColor Cyan

