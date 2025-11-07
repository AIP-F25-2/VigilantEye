# Troubleshooting: Library Detection Issues

## Problem
Backend fails to detect libraries even though they're installed.

## Root Cause
The issue occurs when Python uses the **system Python** instead of the **virtual environment Python**. This happens when:

1. Virtual environment activation doesn't work properly
2. Using `python` command directly instead of `venv\Scripts\python.exe`
3. IDE/terminal using wrong Python interpreter
4. Multiple Python installations on system

## ✅ Solutions

### Solution 1: Use Batch Files (Recommended)
Always use the provided batch files:
```cmd
cd backend
start.bat              # Normal mode
start-debug.bat        # Debug mode
```

These batch files **explicitly use** `venv\Scripts\python.exe`, so they always work.

### Solution 2: Use Explicit Python Path
Never use plain `python` command. Always use:
```cmd
cd backend
venv\Scripts\python.exe run.py
```

### Solution 3: Check Your Environment
Run the diagnostic tool:
```cmd
cd backend
check-python.bat
```

This will show:
- Which Python is being used
- Which libraries are installed
- If venv is being used correctly

### Solution 4: Reinstall Libraries
If libraries are missing:
```cmd
cd backend
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Solution 5: Verify Venv Activation
If using manual activation:
```cmd
cd backend
venv\Scripts\activate.bat
python --version  # Should show venv Python
python -c "import sys; print(sys.executable)"  # Should show venv path
```

## 🔍 Diagnostic Steps

### Step 1: Check Which Python is Running
```cmd
cd backend
python -c "import sys; print(sys.executable)"
```

**Expected**: Should show `...\backend\venv\Scripts\python.exe`
**If wrong**: You're using system Python!

### Step 2: Check if Libraries are Installed
```cmd
cd backend
venv\Scripts\python.exe -c "import fastapi; print('OK')"
```

**If error**: Libraries not installed in venv

### Step 3: Check Python Path
```cmd
cd backend
venv\Scripts\python.exe -c "import sys; [print(p) for p in sys.path[:5]]"
```

Should show venv site-packages path

## 🛠️ Common Scenarios

### Scenario 1: Running `python run.py` directly
**Problem**: Uses system Python
**Fix**: Use `venv\Scripts\python.exe run.py` or `start.bat`

### Scenario 2: IDE Using Wrong Python
**Problem**: IDE configured to use system Python
**Fix**: Configure IDE to use `backend\venv\Scripts\python.exe`

### Scenario 3: Multiple Python Installations
**Problem**: System has multiple Pythons, wrong one being used
**Fix**: Always use explicit venv path

### Scenario 4: Libraries Installed in Wrong Location
**Problem**: Libraries installed in system Python instead of venv
**Fix**: Uninstall from system, install in venv:
```cmd
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## ✅ Verification

After applying fixes, verify:
```cmd
cd backend
venv\Scripts\python.exe -c "import fastapi, uvicorn, sqlalchemy; print('All OK!')"
```

Should print "All OK!" without errors.

## 📝 Updated Files

The following files have been updated to always use venv Python:

1. **`backend/start.bat`** - Uses `venv\Scripts\python.exe`
2. **`backend/start-debug.bat`** - Uses `venv\Scripts\python.exe`
3. **`START_ALL.bat`** - Uses `venv\Scripts\python.exe`
4. **`backend/run.py`** - Enhanced with environment checks
5. **`backend/check-python.bat`** - New diagnostic tool

## 🎯 Best Practices

1. ✅ **Always use batch files** (`start.bat`, `start-debug.bat`)
2. ✅ **Never use plain `python`** - use `venv\Scripts\python.exe`
3. ✅ **Check environment first** - run `check-python.bat`
4. ✅ **Verify venv** - ensure venv exists and is active
5. ✅ **Reinstall if needed** - libraries in wrong location

## 🔧 Quick Fix Commands

```cmd
# Navigate to backend
cd backend

# Verify venv exists
dir venv\Scripts\python.exe

# Check libraries
venv\Scripts\python.exe -c "import fastapi"

# Reinstall if needed
venv\Scripts\python.exe -m pip install -r requirements.txt

# Run server
venv\Scripts\python.exe run.py
```

## 🎵 librosa Installation Issues

### Problem: ModuleNotFoundError: No module named 'librosa'

This error occurs even after installing librosa because:

1. **librosa installed in wrong Python environment** (system vs venv)
2. **Missing dependencies** (soundfile, numpy, scipy)
3. **Using wrong Python interpreter** when running the app

### ✅ Quick Fix

Run the librosa fix script:
```cmd
cd backend
fix-librosa.bat
```

This script will:
- Check if librosa is installed correctly
- Install missing dependencies (soundfile, numpy, scipy)
- Verify the installation
- Show you which Python is being used

### Manual Fix Steps

1. **Check which Python you're using:**
   ```cmd
   cd backend
   python -c "import sys; print(sys.executable)"
   ```
   Should show: `...\backend\venv\Scripts\python.exe`

2. **Install librosa in venv:**
   ```cmd
   cd backend
   venv\Scripts\python.exe -m pip install --upgrade numpy scipy soundfile librosa==0.10.1
   ```

3. **Verify installation:**
   ```cmd
   venv\Scripts\python.exe -c "import librosa; print('✅ librosa:', librosa.__version__)"
   ```

4. **If still not working, try reinstalling:**
   ```cmd
   cd backend
   venv\Scripts\python.exe -m pip uninstall librosa soundfile -y
   venv\Scripts\python.exe -m pip install librosa==0.10.1 soundfile
   ```

### Common Causes

1. **Installed in system Python instead of venv:**
   - You ran `pip install librosa` instead of `venv\Scripts\python.exe -m pip install librosa`
   - **Fix**: Always use `venv\Scripts\python.exe -m pip`

2. **Running app with wrong Python:**
   - You ran `python run.py` instead of `venv\Scripts\python.exe run.py`
   - **Fix**: Use `start.bat` or explicit venv path

3. **Missing dependencies:**
   - librosa requires soundfile, numpy, scipy
   - **Fix**: Run `fix-librosa.bat` or install dependencies manually

### Verification

After fixing, verify librosa works:
```cmd
cd backend
venv\Scripts\python.exe -c "import librosa; import soundfile; print('✅ librosa:', librosa.__version__)"
```

Should print: `✅ librosa: 0.10.1` (or similar version)

## 🆘 Still Having Issues?

1. Run `check-python.bat` and share output
2. Run `fix-librosa.bat` for librosa-specific issues
3. Check error message - it will show which Python is being used
4. Verify venv exists: `dir backend\venv\Scripts\python.exe`
5. Try reinstalling: `venv\Scripts\python.exe -m pip install -r requirements.txt`

