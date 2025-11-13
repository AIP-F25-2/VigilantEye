# Quick Start Script - Use SQLite instead of MySQL
# This allows you to test the application without setting up MySQL

Write-Host "🔧 Switching to SQLite database..." -ForegroundColor Yellow

# Set SQLite as database
$env:DATABASE_URL = "sqlite:///vigilanteye.db"

Write-Host "✅ Database URL set to: $env:DATABASE_URL" -ForegroundColor Green
Write-Host ""
Write-Host "📝 To use SQLite, run:" -ForegroundColor Cyan
Write-Host "   `$env:DATABASE_URL = 'sqlite:///vigilanteye.db'" -ForegroundColor White
Write-Host "   python run.py" -ForegroundColor White
Write-Host ""
Write-Host "Or run this script and then start the server:" -ForegroundColor Cyan
Write-Host "   .\quick_start_sqlite.ps1" -ForegroundColor White
Write-Host "   python run.py" -ForegroundColor White

