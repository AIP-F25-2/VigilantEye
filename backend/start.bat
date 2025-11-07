@echo off
REM VigilantEYE Backend Startup Script (Windows)

echo ==================================
echo 🚀 VigilantEYE Backend Startup
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

REM Check if .env exists and is valid
set ENV_VALID=0
if exist ".env" (
    REM Check if .env contains Python code (invalid format)
    findstr /C:"from pydantic" ".env" >nul 2>&1
    if not errorlevel 1 (
        echo ⚠️  .env file is corrupted (contains Python code)!
        echo Backing up corrupted .env to .env.backup...
        copy /Y .env .env.backup >nul 2>&1
        set ENV_VALID=0
    ) else (
        REM Check if .env has valid format (contains KEY=VALUE)
        findstr /R "^[A-Z_]*=" ".env" >nul 2>&1
        if not errorlevel 1 (
            set ENV_VALID=1
        ) else (
            echo ⚠️  .env file appears to be invalid!
            set ENV_VALID=0
        )
    )
)

if "%ENV_VALID%"=="0" (
    echo ⚠️  .env file not found or invalid!
    if exist "env.example" (
        echo Copying env.example to .env...
        copy /Y env.example .env >nul 2>&1
        echo ✅ .env file created from env.example
        echo ⚠️  Please edit .env with your configuration if needed
    ) else (
        echo ❌ env.example not found. Please create .env file manually.
        pause
        exit /b 1
    )
)

REM Check if database tables exist (optional check)
echo.
echo Checking database connection...
%PYTHON_EXE% -c "import sys; sys.path.insert(0, '.'); from src.config import get_settings; s = get_settings(); print(f'Database: {s.db_name}')" 2>nul

REM Check if debug mode requested
set DEBUG_MODE=%1
if "%DEBUG_MODE%"=="debug" (
    echo.
    echo 🐛 DEBUG MODE ENABLED
    echo ============================================
    set APP_DEBUG=true
    set APP_ENV=development
    set LOG_LEVEL=DEBUG
)

REM Start the server
echo.
echo ============================================
if "%DEBUG_MODE%"=="debug" (
    echo Starting Backend Server - DEBUG MODE
    echo ============================================
    echo Backend API:    http://localhost:8000
    echo API Docs:       http://localhost:8000/api/docs
    echo Log Level:      DEBUG
    echo Auto-reload:    Enabled
    echo SQL Logging:    Enabled
) else (
    echo Starting Backend Server...
    echo ============================================
    echo Backend API:    http://localhost:8000
    echo API Docs:       http://localhost:8000/api/docs
)
echo ============================================
echo.
echo Using Python: %PYTHON_EXE%
echo.
%PYTHON_EXE% run.py
