@echo off
REM VigilantEYE Backend Startup Script - Debug Mode (Windows)

echo ==================================
echo 🐛 VigilantEYE Backend - Debug Mode
echo ==================================

REM Change to backend directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\" (
    echo ❌ Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
    echo ✅ Virtual environment created and dependencies installed!
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Use venv Python explicitly (more reliable than activation)
set PYTHON_EXE=venv\Scripts\python.exe

REM Check if dependencies are installed
%PYTHON_EXE% -c "import fastapi" 2>nul
if errorlevel 1 (
    echo 📦 Installing dependencies...
    %PYTHON_EXE% -m pip install --upgrade pip
    %PYTHON_EXE% -m pip install -r requirements.txt
)

REM Set debug environment variables
set APP_DEBUG=true
set APP_ENV=development
set LOG_LEVEL=DEBUG

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found!
    if exist "env.example" (
        echo Copying env.example to .env...
        copy env.example .env
        echo ⚠️  Please edit .env with your configuration
    ) else (
        echo ⚠️  env.example not found. Please create .env file manually.
    )
)

REM Check if database tables exist (optional check)
echo.
echo Checking database connection...
%PYTHON_EXE% -c "import sys; sys.path.insert(0, '.'); from src.config import get_settings; s = get_settings(); print(f'Database: {s.db_name}')" 2>nul

REM Start the server in debug mode
echo.
echo ============================================
echo Starting Backend Server - DEBUG MODE
echo ============================================
echo Backend API:    http://localhost:8000
echo API Docs:       http://localhost:8000/api/docs
echo Log Level:      DEBUG
echo Auto-reload:    Enabled
echo SQL Logging:    Enabled
echo ============================================
echo.
echo Using Python: %PYTHON_EXE%
echo.
%PYTHON_EXE% run.py

