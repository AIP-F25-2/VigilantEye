# VigilantEYE Backend - Complete Installation Guide

## Step-by-Step Installation

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
```

**Linux/Mac:**
```bash
python3 -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt.

### Step 4: Upgrade pip
```bash
python -m pip install --upgrade pip
```

### Step 5: Install Dependencies

**Option 1: Install all dependencies (Recommended)**
```bash
pip install -r requirements.txt
```

**Option 2: Install with development tools**
```bash
pip install -r requirements-dev.txt
```

**Option 3: Use modular requirements (Alternative)**
```bash
pip install -r requirements/development.txt
```

This will take a few minutes. Wait for it to complete.

### Step 6: Verify Installation
```bash
python -c "import uvicorn; print('✅ uvicorn installed')"
python -c "import fastapi; print('✅ fastapi installed')"
python -c "from jose import jwt; print('✅ jose installed')"
```

### Step 7: Setup Environment
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` file with your MySQL credentials.

### Step 8: Create Database
```sql
mysql -u root -p
CREATE DATABASE vigilanteye_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### Step 9: Run Database Migrations
```bash
python scripts/migrate.py create
```

### Step 10: Start the Server
```bash
python run.py
```

## Quick Installation (Automated)

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'uvicorn'

**Cause:** Dependencies not installed or wrong virtual environment activated.

**Solution:**
```bash
# Make sure virtual environment is activated (you should see (venv) in prompt)
# If not, activate it:
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# Then install dependencies:
pip install -r requirements.txt
# or for development:
pip install -r requirements-dev.txt
```

### Issue: Wrong virtual environment

**Check which Python you're using:**
```bash
# Windows
where python

# Linux/Mac
which python
```

Should show path inside your `venv` folder.

### Issue: python-jose conflict

```bash
pip uninstall jose python-jose -y
pip install python-jose[cryptography]==3.3.0
```

## Complete Fresh Install

If you have issues, start completely fresh:

```bash
# 1. Delete virtual environment
# Windows
rmdir /s /q venv

# Linux/Mac
rm -rf venv

# 2. Delete any __pycache__ folders
# Windows
for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"

# Linux/Mac
find . -type d -name __pycache__ -exec rm -rf {} +

# 3. Create new virtual environment
python -m venv venv

# 4. Activate it
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# 5. Upgrade pip
python -m pip install --upgrade pip

# 6. Install dependencies
pip install -r requirements.txt
# or for development:
pip install -r requirements-dev.txt

# 7. Verify
pip list
```

## Verify Your Setup

Run this command to check everything:
```bash
python -c "
import sys
import uvicorn
import fastapi
import sqlalchemy
from jose import jwt
print('✅ All packages installed correctly!')
print(f'Python: {sys.version}')
print(f'FastAPI: {fastapi.__version__}')
print(f'SQLAlchemy: {sqlalchemy.__version__}')
"
```

## Next Steps

After successful installation:
1. ✅ Dependencies installed
2. ⚙️ Configure `.env` with your settings
3. 🗄️ Create MySQL database
4. 📊 Run migrations
5. 🚀 Start server with `python run.py`
