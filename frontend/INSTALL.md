# VigilantEYE Frontend - Complete Installation Guide

## Step-by-Step Installation

### Step 1: Navigate to Frontend Directory
```bash
cd frontend
```

### Step 2: Install Node.js Dependencies
```bash
npm install
```

This will take a few minutes. Wait for it to complete.

### Step 3: Setup Environment
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

The default `.env` should work if your backend is running on port 8000:
```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=VigilantEYE
```

### Step 4: Start Development Server
```bash
npm run dev
```

### Step 5: Open in Browser
```
http://localhost:3000
```

## Quick Installation (One Command)

```bash
cd frontend && npm install && npm run dev
```

## Troubleshooting

### Issue: npm not found

**Solution:** Install Node.js from https://nodejs.org/
- Download LTS version (18.x or higher)
- Run installer
- Restart terminal

### Issue: Port 3000 already in use

**Solution:** Kill the process or use different port
```bash
# Windows - Find and kill process
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :3000
kill -9 <PID>

# Or run on different port
npm run dev -- --port 3001
```

### Issue: Module not found errors

**Solution:** Delete node_modules and reinstall
```bash
# Windows
rmdir /s /q node_modules
del package-lock.json
npm install

# Linux/Mac
rm -rf node_modules package-lock.json
npm install
```

### Issue: CORS errors

**Make sure:**
1. Backend is running on port 8000
2. Frontend `.env` has correct `VITE_API_URL`
3. Backend `.env` has correct `CORS_ORIGINS`

## Verify Your Setup

```bash
# Check Node.js version (should be 18+)
node --version

# Check npm version
npm --version

# List installed packages
npm list --depth=0
```

## Next Steps

After successful installation:
1. ✅ Frontend running at http://localhost:3000
2. 🔐 Click "Sign up" to create account
3. 📧 Use email like: demo@vigilanteye.com
4. 🔑 Password: DemoPass123
5. 🎉 Start using the dashboard!
