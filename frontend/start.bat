@echo off
REM VigilantEYE Frontend Startup Script (Windows)

echo ==================================
echo 🚀 VigilantEYE Frontend Startup
echo ==================================

REM Change to frontend directory
cd /d "%~dp0"

REM Check if node_modules exists
if not exist "node_modules\" (
    echo 📦 node_modules not found!
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ❌ Failed to install dependencies!
        pause
        exit /b 1
    )
)

REM Check if .env exists (optional)
if not exist ".env" (
    if exist ".env.example" (
        echo ⚠️  .env file not found!
        echo Copying .env.example to .env...
        copy .env.example .env
    )
)

echo.
echo ============================================
echo Starting Frontend Development Server...
echo ============================================
echo Frontend: http://localhost:5173
echo ============================================
echo.
call npm run dev
