@echo off
REM Install critical dependencies that are commonly missing

echo ====================================
echo 📦 Installing Critical Dependencies
echo ====================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ❌ Virtual environment not found!
    pause
    exit /b 1
)

set PYTHON_EXE=venv\Scripts\python.exe

echo Installing critical dependencies...
echo.

REM Core dependencies
echo [1/8] Installing email-validator...
%PYTHON_EXE% -m pip install email-validator --quiet

echo [2/8] Installing facenet-pytorch...
%PYTHON_EXE% -m pip install facenet-pytorch --quiet

echo [3/8] Installing easyocr...
%PYTHON_EXE% -m pip install easyocr --quiet

echo [4/8] Installing ultralytics...
%PYTHON_EXE% -m pip install ultralytics --quiet

echo [5/8] Installing transformers...
%PYTHON_EXE% -m pip install transformers --quiet

echo [6/8] Installing openai...
%PYTHON_EXE% -m pip install openai --quiet

echo [7/8] Installing deepface...
%PYTHON_EXE% -m pip install deepface --quiet

echo [8/8] Installing chromadb...
%PYTHON_EXE% -m pip install chromadb --quiet

echo [9/9] Installing librosa (audio processing)...
%PYTHON_EXE% -m pip install librosa soundfile --quiet

echo.
echo ====================================
echo ✅ Installation Complete
echo ====================================
echo.
echo Verifying installations...
echo.

%PYTHON_EXE% -c "import email_validator; print('✅ email-validator')" 2>nul || echo "❌ email-validator"
%PYTHON_EXE% -c "import facenet_pytorch; print('✅ facenet-pytorch')" 2>nul || echo "❌ facenet-pytorch"
%PYTHON_EXE% -c "import easyocr; print('✅ easyocr')" 2>nul || echo "❌ easyocr"
%PYTHON_EXE% -c "import ultralytics; print('✅ ultralytics')" 2>nul || echo "❌ ultralytics"
%PYTHON_EXE% -c "import transformers; print('✅ transformers')" 2>nul || echo "❌ transformers"
%PYTHON_EXE% -c "import openai; print('✅ openai')" 2>nul || echo "❌ openai"
%PYTHON_EXE% -c "import deepface; print('✅ deepface')" 2>nul || echo "❌ deepface"
%PYTHON_EXE% -c "import chromadb; print('✅ chromadb')" 2>nul || echo "❌ chromadb"
%PYTHON_EXE% -c "import librosa; print('✅ librosa')" 2>nul || echo "❌ librosa"
%PYTHON_EXE% -c "import soundfile; print('✅ soundfile')" 2>nul || echo "❌ soundfile"

echo.
echo ====================================
echo Optional: Enable Audio Classification
echo ====================================
echo.
echo To enable audio classification (PANNs), run:
echo   scripts\setup_panns_data.bat
echo.
echo This is optional - the app works fine without it.
echo.
echo ====================================
echo Done! You can now run: python run.py
echo ====================================
echo.
pause

