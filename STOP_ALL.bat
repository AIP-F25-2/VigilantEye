@echo off
REM Stop VigilantEYE Servers (Windows)

echo ============================================
echo 🛑 Stopping VigilantEYE Servers
echo ============================================
echo.

REM Kill processes on ports 8000 (backend) and 5173 (frontend)
echo Stopping backend server (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
)

echo Stopping frontend server (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo ============================================
echo ✅ Servers stopped!
echo ============================================
pause

