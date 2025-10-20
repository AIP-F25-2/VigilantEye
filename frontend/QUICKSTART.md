# VigilantEYE Frontend - Quick Start

Get the frontend running in 3 minutes!

## Prerequisites

- Node.js 18+ installed
- Backend running at `http://localhost:8000`

## Quick Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env

# 4. Start development server
npm run dev
```

Open `http://localhost:3000` in your browser!

## First Time Usage

### 1. Create Account
1. Click "Sign up" on the login page
2. Enter your details:
   - Email: `demo@vigilanteye.com`
   - Username: `demouser`
   - Password: `DemoPass123`
3. Click "Create Account"
4. You'll be automatically logged in

### 2. Dashboard Features

**Upload Video Tab:**
- Click the upload area or drag & drop a video
- Supported formats: MP4, AVI, MOV
- Click "Upload and Analyze"

**Live Camera Tab:**
- Click "Start Camera"
- Allow camera permissions
- Click "Start Recording" to begin
- Click "Stop Recording" when done

## Common Issues

**Camera not working?**
- Allow camera permissions in browser
- Check if another app is using camera
- Try refreshing the page

**Backend connection error?**
- Ensure backend is running: `http://localhost:8000/api/health`
- Check `.env` has correct `VITE_API_URL`

**Build errors?**
```bash
rm -rf node_modules
npm install
```

## Next Steps

- Customize the theme in `tailwind.config.js`
- Add more pages in `src/pages/`
- Integrate AI services for video analysis

Happy coding! 🚀
