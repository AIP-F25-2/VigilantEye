# VigilantEye Routes Structure

## ✅ Fixed Route Conflicts

The application now has properly separated Web (session-based) and API (JWT-based) authentication routes.

## 📋 Route Mappings

### Web Routes (Session-based Authentication)
Blueprint: `web_auth_bp` (registered at root `/`)

| Method | Route | Function | Description |
|--------|-------|----------|-------------|
| GET/POST | `/login` | `web_auth.login()` | Login page and handler |
| GET/POST | `/register` | `web_auth.register()` | Registration page and handler |
| GET | `/logout` | `web_auth.logout()` | Logout handler |

### API Routes (JWT-based Authentication)
Blueprint: `auth_bp` (registered at `/api/auth`)

| Method | Route | Function | Description |
|--------|-------|----------|-------------|
| POST | `/api/auth/register` | `auth.register()` | API user registration (returns user data) |
| POST | `/api/auth/login` | `auth.login()` | API login (returns JWT tokens) |
| POST | `/api/auth/refresh` | `auth.refresh()` | Refresh JWT tokens |
| POST | `/api/auth/logout` | `auth.logout()` | Revoke JWT tokens |
| GET | `/api/auth/me` | `auth.get_current_user()` | Get current user info |

### Main Routes
Blueprint: `main_bp` (registered at root `/`)

| Method | Route | Function | Description |
|--------|-------|----------|-------------|
| GET | `/` | `main.index()` | Landing page |
| GET | `/dashboard` | `main.dashboard()` | User dashboard (requires login) |
| GET | `/profile` | `main.profile()` | User profile (requires login) |
| GET | `/health` | `main.health()` | Health check endpoint |

### API V2 Routes
Multiple blueprints registered at `/api/v2`

| Blueprint | Routes | Description |
|-----------|--------|-------------|
| `video_bp` | `/api/v2/videos/*` | Video management |
| `recording_bp` | `/api/v2/recordings/*` | Recording management |
| `project_bp` | `/api/v2/projects/*` | Project management |

## 🔑 Authentication Flow

### Web (Browser-based)
1. User visits `/login`
2. Submits credentials
3. Server creates Flask session
4. User redirected to `/dashboard`
5. Session persists across requests

### API (Programmatic)
1. Client POSTs to `/api/auth/login`
2. Server returns JWT access + refresh tokens
3. Client includes token in `Authorization: Bearer <token>` header
4. Token validated on each API request

## 📁 File Structure

```
app/
├── controllers/
│   ├── __init__.py
│   ├── main.py              # Main web routes
│   ├── web_auth_controller.py  # NEW: Web authentication
│   ├── auth_controller.py   # API authentication
│   ├── video_controller.py
│   ├── recording_controller.py
│   └── project_controller.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── profile.html
│   └── auth/
│       ├── login.html
│       └── register.html
└── __init__.py              # App initialization & blueprint registration
```

## 🔧 Template URL References

### Updated to use `web_auth` blueprint:
- `{{ url_for('web_auth.login') }}` → `/login`
- `{{ url_for('web_auth.register') }}` → `/register`
- `{{ url_for('web_auth.logout') }}` → `/logout`

### Main routes:
- `{{ url_for('main.index') }}` → `/`
- `{{ url_for('main.dashboard') }}` → `/dashboard`
- `{{ url_for('main.profile') }}` → `/profile`

## ✅ Benefits of This Structure

1. **No Route Conflicts**: Web and API routes are completely separated
2. **Clear Separation**: Different authentication mechanisms for different use cases
3. **Scalable**: Easy to add more routes to either system
4. **RESTful**: API follows REST principles
5. **User-Friendly**: Web interface uses sessions (no token management needed)

## 🧪 Testing

### Test Web Routes (Browser)
1. Visit: http://localhost:8000
2. Click "Get started" → `/register`
3. Create account and login → `/login`
4. View dashboard → `/dashboard`

### Test API Routes (CLI/Postman)
```bash
# Register via API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"api@test.com","password":"pass123","username":"apiuser"}'

# Login via API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"api@test.com","password":"pass123"}'
```

## 🚀 Deployment

After these changes:
1. Build Docker image
2. Push to Azure Container Registry
3. Restart Azure Container Instance

```bash
docker build -t vigilanteyeacr.azurecr.io/vigilanteye-web:latest .
docker push vigilanteyeacr.azurecr.io/vigilanteye-web:latest
az container restart --resource-group vigilanteye-docker-rg --name vigilanteye-app
```

---

**Last Updated**: October 8, 2025
**Status**: ✅ Routes Properly Configured
