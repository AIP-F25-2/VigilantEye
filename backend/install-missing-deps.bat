@echo off
REM Install missing dependencies from requirements.txt, skipping version conflicts

echo ====================================
echo 📦 Installing Missing Dependencies
echo ====================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    echo Please run setup.bat first or create venv manually.
    pause
    exit /b 1
)

set PYTHON_EXE=venv\Scripts\python.exe

echo Installing dependencies from requirements.txt...
echo This may take several minutes...
echo.

REM Install dependencies one by one, skipping errors for version conflicts
for /f "tokens=*" %%i in (requirements.txt) do (
    REM Skip comments and empty lines
    echo %%i | findstr /R "^[^#]*[a-zA-Z]" >nul 2>&1
    if not errorlevel 1 (
        REM Check if it's a package specification
        echo %%i | findstr /R "==" >nul 2>&1
        if not errorlevel 1 (
            echo Installing: %%i
            %PYTHON_EXE% -m pip install "%%i" --quiet 2>nul
            if errorlevel 1 (
                echo ⚠️  Warning: Failed to install %%i (may be version conflict, skipping...)
            )
        )
    )
)

echo.
echo ====================================
echo ✅ Installation Complete
echo ====================================
echo.
echo Verifying critical dependencies...
echo.

REM Check critical dependencies
%PYTHON_EXE% -c "import fastapi; print('✅ fastapi')" 2>nul || echo "❌ fastapi"
%PYTHON_EXE% -c "import uvicorn; print('✅ uvicorn')" 2>nul || echo "❌ uvicorn"
%PYTHON_EXE% -c "import facenet_pytorch; print('✅ facenet_pytorch')" 2>nul || echo "❌ facenet_pytorch"
%PYTHON_EXE% -c "import easyocr; print('✅ easyocr')" 2>nul || echo "❌ easyocr"
%PYTHON_EXE% -c "import ultralytics; print('✅ ultralytics')" 2>nul || echo "❌ ultralytics"
%PYTHON_EXE% -c "import email_validator; print('✅ email_validator')" 2>nul || echo "❌ email_validator"

echo.
echo Done! You can now run: python run.py
echo.
pause

