@echo off
REM VigilantEYE Backend Startup Script (Windows)

echo ==================================
echo 🚀 VigilantEYE Backend Startup
echo ==================================

REM Check if virtual environment exists
if not exist "venv\" (
    echo ❌ Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo 📦 Installing dependencies...
    pip install -r requirements\development.txt
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found!
    echo Copying .env.example to .env...
    copy .env.example .env
    echo ⚠️  Please edit .env with your configuration
    pause
    exit /b 1
)

REM Start the server
echo.
echo Starting server...
python run.py
