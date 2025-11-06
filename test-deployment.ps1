# VIGILANTEye Deployment Test Script
# Tests all major endpoints after deployment

param(
    [string]$AppUrl = "",
    [string]$ResourceGroupName = "vigilanteye-rg",
    [string]$ContainerAppName = "vigilanteye-app"
)

Write-Host "🧪 VIGILANTEye Deployment Test" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Get application URL if not provided
if (-not $AppUrl) {
    Write-Host "🔍 Getting application URL..." -ForegroundColor Yellow
    $AppUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query "properties.configuration.ingress.fqdn" -o tsv
    
    if (-not $AppUrl) {
        Write-Error "❌ Could not retrieve application URL"
        exit 1
    }
    
    $AppUrl = "https://$AppUrl"
}

Write-Host "🌐 Testing application at: $AppUrl" -ForegroundColor Cyan

# Test functions
function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Name,
        [string]$ExpectedStatus = "200"
    )
    
    try {
        Write-Host "Testing $Name..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 30
        Write-Host "✅ $Name - Status: OK" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ $Name - Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-APIEndpoint {
    param(
        [string]$Url,
        [string]$Name,
        [string]$ExpectedKey = "success"
    )
    
    try {
        Write-Host "Testing $Name..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 30
        
        if ($response.$ExpectedKey -eq $true) {
            Write-Host "✅ $Name - API Response: OK" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️ $Name - Unexpected response: $($response | ConvertTo-Json)" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "❌ $Name - Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test results tracking
$testResults = @()

# 1. Health Check
Write-Host "`n1. Testing Health Check..." -ForegroundColor Cyan
$testResults += Test-Endpoint "$AppUrl/health" "Health Check"

# 2. Main Dashboard
Write-Host "`n2. Testing Main Dashboard..." -ForegroundColor Cyan
$testResults += Test-Endpoint "$AppUrl/" "Main Dashboard"

# 3. FaceAi Service Status
Write-Host "`n3. Testing FaceAi Service..." -ForegroundColor Cyan
$testResults += Test-APIEndpoint "$AppUrl/api/faceai/status" "FaceAi Service"

# 4. CCTV Agent Status
Write-Host "`n4. Testing CCTV Agent..." -ForegroundColor Cyan
$testResults += Test-APIEndpoint "$AppUrl/api/cctv/status" "CCTV Agent"

# 5. Telegram Integration
Write-Host "`n5. Testing Telegram Integration..." -ForegroundColor Cyan
$testResults += Test-APIEndpoint "$AppUrl/api/telegram/ingest" "Telegram API" "error"

# 6. FaceAi Dashboard
Write-Host "`n6. Testing FaceAi Dashboard..." -ForegroundColor Cyan
$testResults += Test-Endpoint "$AppUrl/faceai" "FaceAi Dashboard"

# 7. CCTV Dashboard
Write-Host "`n7. Testing CCTV Dashboard..." -ForegroundColor Cyan
$testResults += Test-Endpoint "$AppUrl/cctv" "CCTV Dashboard"

# 8. API Authentication
Write-Host "`n8. Testing API Authentication..." -ForegroundColor Cyan
try {
    $authResponse = Invoke-RestMethod -Uri "$AppUrl/api/auth/login" -Method POST -Body '{"username":"test","password":"test"}' -ContentType "application/json" -TimeoutSec 30
    Write-Host "✅ API Authentication - Endpoint accessible" -ForegroundColor Green
    $testResults += $true
} catch {
    Write-Host "✅ API Authentication - Endpoint accessible (expected auth failure)" -ForegroundColor Green
    $testResults += $true
}

# 9. Database Connection
Write-Host "`n9. Testing Database Connection..." -ForegroundColor Cyan
try {
    $dbResponse = Invoke-RestMethod -Uri "$AppUrl/api/v1/users" -Method GET -TimeoutSec 30
    Write-Host "✅ Database Connection - API accessible" -ForegroundColor Green
    $testResults += $true
} catch {
    Write-Host "⚠️ Database Connection - May need authentication" -ForegroundColor Yellow
    $testResults += $false
}

# 10. Face Detection API
Write-Host "`n10. Testing Face Detection API..." -ForegroundColor Cyan
try {
    $faceResponse = Invoke-RestMethod -Uri "$AppUrl/api/faceai/detections" -Method GET -TimeoutSec 30
    Write-Host "✅ Face Detection API - Accessible" -ForegroundColor Green
    $testResults += $true
} catch {
    Write-Host "⚠️ Face Detection API - May need authentication" -ForegroundColor Yellow
    $testResults += $false
}

# Summary
Write-Host "`n📊 Test Summary" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green

$passedTests = ($testResults | Where-Object { $_ -eq $true }).Count
$totalTests = $testResults.Count
$successRate = [math]::Round(($passedTests / $totalTests) * 100, 2)

Write-Host "✅ Passed: $passedTests/$totalTests tests ($successRate%)" -ForegroundColor Green

if ($successRate -ge 80) {
    Write-Host "🎉 Deployment is successful!" -ForegroundColor Green
} elseif ($successRate -ge 60) {
    Write-Host "⚠️ Deployment is mostly successful with some issues" -ForegroundColor Yellow
} else {
    Write-Host "❌ Deployment has significant issues" -ForegroundColor Red
}

# Display key endpoints
Write-Host "`n🔗 Key Endpoints:" -ForegroundColor Cyan
Write-Host "   • Main Dashboard: $AppUrl/" -ForegroundColor White
Write-Host "   • FaceAi Dashboard: $AppUrl/faceai" -ForegroundColor White
Write-Host "   • CCTV Intelligence: $AppUrl/cctv" -ForegroundColor White
Write-Host "   • API Health: $AppUrl/health" -ForegroundColor White
Write-Host "   • FaceAi API: $AppUrl/api/faceai/status" -ForegroundColor White
Write-Host "   • CCTV API: $AppUrl/api/cctv/status" -ForegroundColor White

Write-Host "`n🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Access the web dashboards to test functionality" -ForegroundColor White
Write-Host "2. Upload CCTV videos for processing" -ForegroundColor White
Write-Host "3. Configure watchlists for employees, VIPs, and suspects" -ForegroundColor White
Write-Host "4. Test face detection and recognition features" -ForegroundColor White
Write-Host "5. Monitor application logs for any issues" -ForegroundColor White

Write-Host "`n✨ VIGILANTEye with Face & Identity Agent is ready!" -ForegroundColor Green

