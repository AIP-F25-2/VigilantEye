# Local Docker Testing Guide

## 🐳 Files Created

I've created three files for local Docker testing:

1. **`docker-compose.local.yml`** - Docker Compose configuration
2. **`test-local.ps1`** - PowerShell script for Windows
3. **`test-local.sh`** - Bash script for Linux/Mac

## 🚀 Quick Start

### Option 1: Using the Test Script (Easiest)

**Windows (PowerShell):**
```powershell
.\test-local.ps1
```

**Linux/Mac (Bash):**
```bash
chmod +x test-local.sh
./test-local.sh
```

### Option 2: Manual Docker Compose Commands

```bash
# Step 1: Clean up any existing containers
docker-compose -f docker-compose.local.yml down -v

# Step 2: Build and start containers
docker-compose -f docker-compose.local.yml up --build -d

# Step 3: Wait for initialization (30 seconds)
# Then check logs
docker-compose -f docker-compose.local.yml logs -f app

# Step 4: Test the application
# Open browser: http://localhost:8000
```

## 📦 What Gets Created

The Docker Compose setup creates:

1. **MySQL Database Container**
   - Port: `3306`
   - Database: `flaskapi`
   - User: `vigilanteye`
   - Password: `YourPassword123!`

2. **VIGILANTEye Application Container**
   - Port: `8000`
   - Auto-runs migrations
   - Connected to local MySQL

## 🌐 Access Points

Once running, you can access:

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Homepage |
| http://localhost:8000/login | Login page |
| http://localhost:8000/register | Registration page |
| http://localhost:8000/dashboard | Dashboard (after login) |
| http://localhost:8000/health | Health check API |

## 🧪 Test the Application

### 1. Register a New User

**Via Web Interface:**
1. Go to http://localhost:8000/register
2. Fill in the form:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `Test123!@#`
3. Submit

**Via API:**
```powershell
$body = @{
    username = "testuser"
    email = "test@example.com"
    password = "Test123!@#"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/auth/register" -Method POST -Body $body -ContentType "application/json"
```

### 2. Login

**Via Web Interface:**
1. Go to http://localhost:8000/login
2. Enter credentials
3. View dashboard

**Via API:**
```powershell
$body = @{
    email = "test@example.com"
    password = "Test123!@#"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -Body $body -ContentType "application/json"
```

### 3. Test Health Endpoint

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

## 📊 Monitoring

### View All Logs
```bash
docker-compose -f docker-compose.local.yml logs -f
```

### View Application Logs Only
```bash
docker-compose -f docker-compose.local.yml logs -f app
```

### View Database Logs Only
```bash
docker-compose -f docker-compose.local.yml logs -f db
```

### Check Container Status
```bash
docker-compose -f docker-compose.local.yml ps
```

## 🔧 Management Commands

### Stop Containers (keep data)
```bash
docker-compose -f docker-compose.local.yml stop
```

### Start Stopped Containers
```bash
docker-compose -f docker-compose.local.yml start
```

### Restart Containers
```bash
docker-compose -f docker-compose.local.yml restart
```

### Rebuild and Restart
```bash
docker-compose -f docker-compose.local.yml up --build -d
```

### Stop and Remove Containers (delete data)
```bash
docker-compose -f docker-compose.local.yml down -v
```

### Execute Command in App Container
```bash
docker-compose -f docker-compose.local.yml exec app bash
```

### Run Database Migrations
```bash
docker-compose -f docker-compose.local.yml exec app flask db upgrade
```

## 🐛 Troubleshooting

### Port Already in Use

If port 8000 or 3306 is already in use:

**Option 1: Stop conflicting services**
```powershell
# Find what's using the port
netstat -ano | findstr :8000
netstat -ano | findstr :3306

# Stop the process or change ports in docker-compose.local.yml
```

**Option 2: Change ports**
Edit `docker-compose.local.yml`:
```yaml
ports:
  - "8001:8000"  # Use port 8001 instead
```

### Container Won't Start

**Check logs:**
```bash
docker-compose -f docker-compose.local.yml logs app
```

**Common issues:**
1. Port conflicts - change ports in docker-compose.local.yml
2. Docker not running - start Docker Desktop
3. Build errors - check Dockerfile syntax

### Database Connection Failed

**Check database is ready:**
```bash
docker-compose -f docker-compose.local.yml exec db mysqladmin -u vigilanteye -pYourPassword123! ping
```

**Reset database:**
```bash
docker-compose -f docker-compose.local.yml down -v
docker-compose -f docker-compose.local.yml up -d
```

### Migrations Failed

**Run migrations manually:**
```bash
# Wait for DB to be ready (30 seconds)
docker-compose -f docker-compose.local.yml exec app flask db upgrade
```

### Static Files Not Loading

**Rebuild the image:**
```bash
docker-compose -f docker-compose.local.yml build --no-cache
docker-compose -f docker-compose.local.yml up -d
```

## 🔍 Database Access

### Connect to MySQL from Host
```bash
mysql -h 127.0.0.1 -P 3306 -u vigilanteye -pYourPassword123! flaskapi
```

### Using MySQL Workbench
- Host: `127.0.0.1` or `localhost`
- Port: `3306`
- Username: `vigilanteye`
- Password: `YourPassword123!`
- Database: `flaskapi`

### Connect via Docker
```bash
docker-compose -f docker-compose.local.yml exec db mysql -u vigilanteye -pYourPassword123! flaskapi
```

## 📁 File Locations in Container

- Application code: `/app`
- Migrations: `/app/migrations`
- Templates: `/app/app/templates`
- Static files: `/app/app/static`

## 🔄 Development Workflow

1. **Make code changes** on your host machine
2. **Rebuild and restart:**
   ```bash
   docker-compose -f docker-compose.local.yml up --build -d
   ```
3. **View logs:**
   ```bash
   docker-compose -f docker-compose.local.yml logs -f app
   ```
4. **Test changes** in browser

## 📝 Environment Variables

The following environment variables are set in docker-compose.local.yml:

```yaml
DATABASE_URL: "mysql+pymysql://vigilanteye:YourPassword123!@db:3306/flaskapi"
SECRET_KEY: "dev-secret-key-local-testing"
JWT_SECRET_KEY: "jwt-secret-string-local"
FLASK_ENV: "development"
```

To change them, edit `docker-compose.local.yml`.

## 🧹 Cleanup

### Remove Everything
```bash
# Stop containers and remove volumes
docker-compose -f docker-compose.local.yml down -v

# Remove images
docker rmi vigilanteye_app-local
docker rmi mysql:8.0
```

### Remove Only App Image
```bash
docker rmi vigilanteye-vigilanteye-app-local
```

## ✅ Verification Checklist

After starting containers, verify:

- [ ] Containers are running: `docker-compose -f docker-compose.local.yml ps`
- [ ] Database is healthy: `docker-compose -f docker-compose.local.yml exec db mysqladmin ping`
- [ ] App is responding: `curl http://localhost:8000/health`
- [ ] Homepage loads: Open http://localhost:8000 in browser
- [ ] Can register user: http://localhost:8000/register
- [ ] Can login: http://localhost:8000/login
- [ ] Dashboard loads: http://localhost:8000/dashboard (after login)

## 🎯 Next Steps After Testing

Once local testing is successful:

1. **Test all features** - registration, login, dashboard
2. **Check API endpoints** - verify all routes work
3. **Test static files** - CSS and JS loading correctly
4. **Deploy to Azure** - use `deploy.ps1` script

## 📚 Related Documentation

- `DEPLOYMENT_GUIDE.md` - Azure deployment
- `FRONTEND_INTEGRATION.md` - Frontend details
- `QUICKSTART.md` - Quick start guide

---

## 🆘 Still Having Issues?

1. Check all logs: `docker-compose -f docker-compose.local.yml logs`
2. Verify Docker is running: `docker --version`
3. Check available ports: `netstat -ano`
4. Try clean rebuild: `docker-compose -f docker-compose.local.yml down -v && docker-compose -f docker-compose.local.yml up --build`

---

**Happy Testing! 🎉**
