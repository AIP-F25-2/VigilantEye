@echo off
REM VigilantEYE Frontend Startup Script (Windows)

echo ==================================
echo 🚀 VigilantEYE Frontend Startup
echo ==================================

REM Check if node_modules exists
if not exist "node_modules\" (
    echo 📦 node_modules not found!
    echo Installing dependencies...
    call npm install
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found!
    echo Copying .env.example to .env...
    copy .env.example .env
)

echo.
echo Starting development server...
echo Frontend will be available at: http://localhost:3000
echo.
call npm run dev
