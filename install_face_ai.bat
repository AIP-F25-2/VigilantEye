@echo off
echo Installing Face AI Dependencies for VigilantEye...
echo.

echo Step 1: Installing basic dependencies...
pip install opencv-python Pillow scikit-learn matplotlib numpy

echo.
echo Step 2: Installing face-recognition (this may take a while)...
echo Note: This requires CMake to be installed
echo Download CMake from: https://cmake.org/download/
echo.

pause

echo Installing face-recognition...
pip install face-recognition

echo.
echo Installation complete!
echo.
echo To enable full Face AI features:
echo 1. Install CMake from https://cmake.org/download/
echo 2. Run this script again
echo 3. Restart the VigilantEye application
echo.
echo The application will work in demo mode without these dependencies.
echo.
pause
