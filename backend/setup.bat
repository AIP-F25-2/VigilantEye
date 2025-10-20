@echo off
REM Setup script for VigilantEYE Backend (Windows)

echo ====================================
echo 🔧 VigilantEYE Backend Setup
echo ====================================

REM Remove old virtual environment
if exist "venv\" (
    echo Removing old virtual environment...
    rmdir /s /q venv
)

REM Create new virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements\development.txt

REM Verify installation
echo.
echo Verifying installation...
python -c "from jose import jwt; print('✅ JWT library installed correctly!')"
python -c "import fastapi; print('✅ FastAPI installed correctly!')"
python -c "import sqlalchemy; print('✅ SQLAlchemy installed correctly!')"

echo.
echo ====================================
echo ✅ Setup Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Edit .env with your MySQL credentials
echo 3. Create database: CREATE DATABASE vigilanteye_db;
echo 4. Run migrations: python scripts\migrate.py create
echo 5. Start server: python run.py
echo.
pause
