# VigilantEYE Frontend

React-based frontend for VigilantEYE AI Video Intelligence System.

## Features

- 🎨 **Modern UI** - Black and gray theme with AI-inspired design
- 🔐 **Authentication** - Sign up and login with JWT tokens
- 📹 **Video Upload** - Upload videos for AI analysis
- 📷 **Live Camera** - Access and record from webcam
- 🎯 **Responsive Design** - Works on all screen sizes
- ⚡ **Fast & Modern** - Built with Vite and React 18

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **Axios** - HTTP client
- **React Router** - Navigation
- **Lucide React** - Icons

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=VigilantEYE
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   └── Logo.jsx        # VigilantEYE logo
│   ├── pages/              # Page components
│   │   ├── Login.jsx       # Login page
│   │   ├── SignUp.jsx      # Sign up page
│   │   └── Dashboard.jsx   # Main dashboard
│   ├── services/           # API services
│   │   └── api.js          # API client
│   ├── store/              # State management
│   │   └── authStore.js    # Auth state
│   ├── App.jsx             # Main app component
│   ├── main.jsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html              # HTML template
├── package.json            # Dependencies
├── vite.config.js          # Vite configuration
└── tailwind.config.js      # Tailwind configuration
```

## Features Details

### Authentication

- **Sign Up**: Create new account with email, username, and password
- **Login**: Authenticate with email and password
- **Auto Login**: Persistent sessions with localStorage
- **Token Refresh**: Automatic token refresh on expiry
- **Protected Routes**: Dashboard only accessible when logged in

### Dashboard

#### Upload Video Tab
- Drag and drop or click to upload
- File validation (video formats only)
- Upload progress indicator
- File size display
- Remove selected file option

#### Live Camera Tab
- Access webcam with permission
- Real-time video preview
- Recording functionality
- Start/stop camera controls
- AI scanning effect overlay

### Design System

#### Colors
- **Primary**: Cyan/Blue (`#0ea5e9`)
- **Background**: Very dark gray (`#020617`)
- **Cards**: Dark gray with transparency
- **Text**: Light gray with hierarchy

#### Components
- Glass morphism effects
- Animated gradients
- Glowing borders on hover
- Scan line animations
- Responsive grid layouts

## API Integration

The frontend connects to the backend API:

```javascript
// Auth endpoints
POST /api/auth/signup      - Create account
POST /api/auth/login       - Login
GET  /api/auth/me          - Get user info
POST /api/auth/refresh     - Refresh token

// Video endpoints (future)
POST /api/video/upload     - Upload video
GET  /api/video/list       - Get videos
```

## State Management

Using Zustand for simple state management:

```javascript
// Auth state
{
  user: User object,
  accessToken: JWT token,
  refreshToken: JWT refresh token,
  isAuthenticated: boolean
}
```

State is persisted to localStorage automatically.

## Camera Access

The app requests webcam access using:
```javascript
navigator.mediaDevices.getUserMedia({
  video: { width: 1280, height: 720 },
  audio: false
})
```

Make sure to allow camera permissions when prompted.

## Building for Production

```bash
# Build
npm run build

# Preview build
npm run preview
```

The build output will be in the `dist/` directory.

## Customization

### Change Theme Colors

Edit `tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your colors here
      }
    }
  }
}
```

### Change Logo

Update `src/components/Logo.jsx` or replace the eye icon.

### Add New Pages

1. Create page in `src/pages/`
2. Add route in `src/App.jsx`
3. Update navigation

## Troubleshooting

### Camera Not Working
- Check browser permissions
- Ensure HTTPS in production (required for camera)
- Try different browser

### API Connection Failed
- Verify backend is running
- Check VITE_API_URL in .env
- Check CORS settings in backend

### Build Errors
- Delete node_modules and reinstall
- Clear Vite cache: `rm -rf node_modules/.vite`
- Update dependencies

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support (iOS 14.5+)
- Camera requires HTTPS in production

## Next Steps

- [ ] Add video analysis results display
- [ ] Implement video history/library
- [ ] Add user settings page
- [ ] Implement admin dashboard
- [ ] Add real-time notifications
- [ ] Connect to AI services
- [ ] Add video playback controls
- [ ] Implement video trimming

## License

© 2024 VigilantEYE. All rights reserved.
