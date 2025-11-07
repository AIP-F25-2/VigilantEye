@echo off
REM Fix librosa installation issues

echo ====================================
echo 🔧 Fixing librosa Installation
echo ====================================
echo.

cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    echo Please run setup.bat first or create venv manually.
    pause
    exit /b 1
)

set PYTHON_EXE=venv\Scripts\python.exe

echo Step 1: Checking current Python environment...
echo.
%PYTHON_EXE% -c "import sys; print(f'Python: {sys.executable}'); print(f'Version: {sys.version}')"
echo.

echo Step 2: Checking if librosa is installed...
%PYTHON_EXE% -c "import librosa; print('✅ librosa is installed'); print(f'Version: {librosa.__version__}'); print(f'Path: {librosa.__file__}')" 2>nul
if errorlevel 1 (
    echo ❌ librosa is NOT installed in venv
    echo.
    echo Step 3: Installing librosa and dependencies...
    echo.
    
    REM Install librosa dependencies first (important for Windows)
    echo [1/4] Installing numpy and scipy (dependencies)...
    %PYTHON_EXE% -m pip install --upgrade numpy scipy --quiet
    
    echo [2/4] Installing soundfile (required for librosa)...
    %PYTHON_EXE% -m pip install --upgrade soundfile --quiet
    
    echo [3/4] Installing librosa...
    %PYTHON_EXE% -m pip install --upgrade librosa==0.10.1 --quiet
    
    echo [4/4] Verifying installation...
    %PYTHON_EXE% -c "import librosa; import soundfile; print('✅ librosa installed successfully'); print(f'librosa version: {librosa.__version__}')" 2>nul
    if errorlevel 1 (
        echo ❌ Installation failed!
        echo.
        echo Trying alternative installation method...
        %PYTHON_EXE% -m pip install librosa --no-cache-dir
        %PYTHON_EXE% -c "import librosa; print('✅ librosa installed successfully')" 2>nul
        if errorlevel 1 (
            echo ❌ Still failed. Please check error messages above.
            pause
            exit /b 1
        )
    )
) else (
    echo.
    echo ✅ librosa is already installed correctly!
    echo.
    echo Step 3: Verifying dependencies...
    %PYTHON_EXE% -c "import soundfile; print('✅ soundfile'); import numpy; print('✅ numpy'); import scipy; print('✅ scipy')" 2>nul
    if errorlevel 1 (
        echo ⚠️  Some dependencies are missing. Installing...
        %PYTHON_EXE% -m pip install soundfile numpy scipy --quiet
    )
)

echo.
echo ====================================
echo ✅ librosa Check Complete
echo ====================================
echo.
echo Final verification:
echo.
%PYTHON_EXE% -c "import librosa; import soundfile; print('✅ librosa: OK'); print('✅ soundfile: OK'); print(f'✅ Version: {librosa.__version__}')" 2>nul
if errorlevel 1 (
    echo ❌ Verification failed!
    echo.
    echo Common issues:
    echo 1. Make sure you're using venv\Scripts\python.exe
    echo 2. Try reinstalling: venv\Scripts\python.exe -m pip uninstall librosa -y ^&^& venv\Scripts\python.exe -m pip install librosa
    echo 3. Check if you have multiple Python installations
    pause
    exit /b 1
) else (
    echo.
    echo ✅ All checks passed! librosa should work now.
    echo.
    echo To test, run:
    echo   venv\Scripts\python.exe -c "import librosa; print('Success!')"
    echo.
)

pause

