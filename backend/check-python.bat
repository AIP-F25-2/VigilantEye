@echo off
REM Diagnostic script to check Python environment and library detection

echo ============================================
echo 🔍 Python Environment Diagnostic Tool
echo ============================================
echo.

cd /d "%~dp0"

echo Checking Python installations...
echo.

REM Check system Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ System Python not found in PATH
) else (
    for /f "delims=" %%i in ('where python') do (
        echo System Python: %%i
        python -c "import sys; print('  Version:', sys.version.split()[0])" 2>nul
        python -c "import sys; print('  Executable:', sys.executable)" 2>nul
        python -c "import fastapi" 2>nul && echo "  ✅ FastAPI installed" || echo "  ❌ FastAPI NOT installed"
    )
)

echo.
echo Checking Virtual Environment...
echo.

if exist "venv\Scripts\python.exe" (
    echo ✅ Virtual environment found
    echo Venv Python: venv\Scripts\python.exe
    
    venv\Scripts\python.exe -c "import sys; print('  Version:', sys.version.split()[0])" 2>nul
    venv\Scripts\python.exe -c "import sys; print('  Executable:', sys.executable)" 2>nul
    
    echo.
    echo Checking installed libraries...
    echo.
    
    venv\Scripts\python.exe -c "import fastapi" 2>nul && echo "  ✅ FastAPI installed" || echo "  ❌ FastAPI NOT installed"
    venv\Scripts\python.exe -c "import uvicorn" 2>nul && echo "  ✅ Uvicorn installed" || echo "  ❌ Uvicorn NOT installed"
    venv\Scripts\python.exe -c "import sqlalchemy" 2>nul && echo "  ✅ SQLAlchemy installed" || echo "  ❌ SQLAlchemy NOT installed"
    venv\Scripts\python.exe -c "import pydantic" 2>nul && echo "  ✅ Pydantic installed" || echo "  ❌ Pydantic NOT installed"
    venv\Scripts\python.exe -c "import pymysql" 2>nul && echo "  ✅ PyMySQL installed" || echo "  ❌ PyMySQL NOT installed"
    
    echo.
    echo Checking Python path...
    venv\Scripts\python.exe -c "import sys; print('  Python Path:'); [print(f'    {p}') for p in sys.path[:5]]"
    
) else (
    echo ❌ Virtual environment NOT found!
    echo Expected location: venv\Scripts\python.exe
    echo.
    echo Please run: python -m venv venv
)

echo.
echo ============================================
echo 💡 Recommendations
echo ============================================
echo.
echo 1. Always use: venv\Scripts\python.exe run.py
echo 2. Or use the batch files: start.bat or start-debug.bat
echo 3. Never use plain 'python' command - it may use system Python
echo 4. If libraries are missing, run: venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause

