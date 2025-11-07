@echo off
REM Fix numpy and opencv-python version conflicts

echo ====================================
echo 🔧 Fixing numpy/opencv-python Conflicts
echo ====================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    pause
    exit /b 1
)

set PYTHON_EXE=venv\Scripts\python.exe

echo Step 1: Checking current versions...
echo.
%PYTHON_EXE% -m pip list | findstr /i "numpy opencv"
echo.

echo Step 2: Uninstalling conflicting packages...
echo.
%PYTHON_EXE% -m pip uninstall -y opencv-python opencv-python-headless numpy
echo.

echo Step 3: Installing compatible numpy version...
echo (Python 3.12 requires numpy ^>= 1.26.0)
echo.
REM Check Python version and install appropriate numpy
%PYTHON_EXE% -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>nul
if errorlevel 1 (
    REM Python < 3.12, use numpy 1.24.3
    echo Installing numpy 1.24.3 for Python ^< 3.12...
    %PYTHON_EXE% -m pip install "numpy==1.24.3" --no-cache-dir
) else (
    REM Python 3.12+, use numpy 1.26.x (compatible with Python 3.12 and opencv)
    echo Installing numpy 1.26.4 for Python 3.12+...
    %PYTHON_EXE% -m pip install "numpy==1.26.4" --no-cache-dir
)
echo.

echo Step 4: Installing opencv-python (not headless to avoid typing conflicts)...
echo.
REM Install opencv-python (not headless) to avoid cv2.typing conflicts
%PYTHON_EXE% -m pip install "opencv-python>=4.8.0,<4.9.0" --no-cache-dir
echo.

echo Step 5: Verifying installation...
echo.
%PYTHON_EXE% -c "import numpy; print('✅ numpy:', numpy.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ numpy import failed!
    pause
    exit /b 1
)

%PYTHON_EXE% -c "import cv2; print('✅ opencv:', cv2.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ opencv import failed!
    pause
    exit /b 1
)

echo.
echo Step 6: Testing imports together...
echo.
REM Test imports in correct order to avoid cv2.typing conflict
%PYTHON_EXE% -c "import sys; sys.path.insert(0, ''); import numpy; import cv2; import typing; print('✅ All imports successful!')" 2>nul
if errorlevel 1 (
    echo ⚠️  Import test failed. Trying workaround...
    echo.
    echo Creating import workaround...
    echo.
    REM Create a workaround script to test
    echo import sys > test_imports.py
    echo import numpy >> test_imports.py
    echo import cv2 >> test_imports.py
    echo # Force import of stdlib typing before cv2.typing >> test_imports.py
    echo import typing as _typing >> test_imports.py
    echo from typing import Any >> test_imports.py
    echo print('✅ All imports successful!') >> test_imports.py
    %PYTHON_EXE% test_imports.py 2>nul
    if errorlevel 1 (
        echo ❌ Still failing. Error details:
        %PYTHON_EXE% test_imports.py
        del test_imports.py 2>nul
        pause
        exit /b 1
    )
    del test_imports.py 2>nul
)

echo.
echo ====================================
echo ✅ Fix Complete!
echo ====================================
echo.
echo Installed versions:
%PYTHON_EXE% -m pip list | findstr /i "numpy opencv"
echo.
echo You can now run: venv\Scripts\python.exe run.py
echo.
pause

