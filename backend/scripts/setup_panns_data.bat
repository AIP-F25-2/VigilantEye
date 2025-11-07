@echo off
REM Setup script for PANNs inference data files (Windows)

echo ====================================
echo 🎵 PANNs Data Setup
echo ====================================

cd /d "%~dp0\.."

if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    pause
    exit /b 1
)

echo Installing requests if needed...
venv\Scripts\python.exe -m pip install requests --quiet

echo Running setup script...
venv\Scripts\python.exe scripts\setup_panns_data.py

pause

