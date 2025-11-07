@echo off
REM Start both Backend and Frontend for VigilantEYE

echo ============================================
echo 🚀 Starting VigilantEYE - Full Stack
echo ============================================
echo.

REM Check if debug mode requested
set DEBUG_MODE=%1
if "%DEBUG_MODE%"=="debug" (
    echo 🐛 DEBUG MODE ENABLED
    echo ============================================
    echo.
)

REM Change to project root directory
cd /d "%~dp0"

REM Check if backend venv exists
if not exist "backend\venv\" (
    echo ❌ Backend virtual environment not found!
    echo Please run: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if frontend node_modules exists
if not exist "frontend\node_modules\" (
    echo ⚠️  Frontend dependencies not found!
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Start Backend in new window
if "%DEBUG_MODE%"=="debug" (
    echo Starting Backend Server in DEBUG MODE...
    start "VigilantEYE Backend (DEBUG)" cmd /k "cd /d %~dp0backend && set APP_DEBUG=true && set APP_ENV=development && set LOG_LEVEL=DEBUG && venv\Scripts\python.exe run.py"
) else (
    echo Starting Backend Server...
    start "VigilantEYE Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe run.py"
)

REM Wait a bit for backend to start
timeout /t 3 /nobreak > nul

REM Start Frontend in new window
echo Starting Frontend Server...
start "VigilantEYE Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo ✅ Both servers starting!
echo ============================================
echo.
echo Backend API:    http://localhost:8000
echo Backend Docs:   http://localhost:8000/api/docs
echo Frontend:       http://localhost:5173
if "%DEBUG_MODE%"=="debug" (
    echo.
    echo 🐛 Backend running in DEBUG MODE
    echo    - Verbose logging enabled
    echo    - SQL query logging enabled
    echo    - Auto-reload enabled
)
echo.
echo Servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
echo Press any key to close this window...
pause > nul
