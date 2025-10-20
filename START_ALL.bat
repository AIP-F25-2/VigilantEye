@echo off
REM Start both Backend and Frontend for VigilantEYE

echo ============================================
echo 🚀 Starting VigilantEYE - Full Stack
echo ============================================
echo.

REM Start Backend in new window
echo Starting Backend Server...
start "VigilantEYE Backend" cmd /k "cd backend && venv\Scripts\activate && python run.py"

REM Wait a bit for backend to start
timeout /t 3 /nobreak > nul

REM Start Frontend in new window
echo Starting Frontend Server...
start "VigilantEYE Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo ✅ Both servers starting!
echo ============================================
echo.
echo Backend:  http://localhost:8000/api/docs
echo Frontend: http://localhost:3000
echo.
echo Press any key to close this window...
pause > nul
