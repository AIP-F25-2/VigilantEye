# Quick Start Guide - VIGILANTEye

## 🚀 Test the Application Locally

### Prerequisites
- Python 3.11+
- MySQL database
- pip package manager

### Step 1: Clone and Setup
```bash
cd C:\Users\Sukjit Singh\Documents\vigi\VigilantEye

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Database
Set environment variables:
```powershell
$env:DATABASE_URL = "mysql+pymysql://your_user:your_password@localhost:3306/your_database"
$env:SECRET_KEY = "your-secret-key-here"
$env:JWT_SECRET_KEY = "jwt-secret-string"
$env:FLASK_ENV = "development"
```

### Step 3: Run Database Migrations
```bash
flask db upgrade
```


### Step 4: Run the Application
```bash
python run.py
```

### Step 5: Access the Application
Open your browser and visit:
- **Homepage**: http://localhost:5000
- **Login**: http://localhost:5000/login
- **Register**: http://localhost:5000/register
- **API Health**: http://localhost:5000/health

## 🧪 Test the Features

### 1. Register a New User
1. Go to http://localhost:5000/register
2. Fill in:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `Test123!@#`
   - Confirm Password: `Test123!@#`
3. Click "Create account"

### 2. Login
1. Go to http://localhost:5000/login
2. Enter credentials:
   - Email: `test@example.com`
   - Password: `Test123!@#`
3. Click "Sign in"

### 3. Test Dashboard
- After login, you'll be redirected to `/dashboard`
- View stats cards (will show 0 until data is added)
- Try quick action buttons

### 4. View Profile
- Click on your username in the navbar
- Select "Profile" from dropdown
- View your account information

### 5. Test API Endpoints
```bash
# Register via API
curl --location --request POST 'http://localhost:5000/api/auth/register' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "api-user@example.com",
  "password": "password123",
  "username": "apiuser"
}'

# Login via API
curl --location --request POST 'http://localhost:5000/api/auth/login' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "api-user@example.com",
  "password": "password123"
}'
```

## 🌐 Test on Azure

### Current Deployment
**URL**: http://vigilanteye-app.eastus.azurecontainer.io:8000

### Test Registration
```bash
curl --location --request POST 'http://vigilanteye-app.eastus.azurecontainer.io:8000/api/auth/register' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "azure-test@example.com",
  "password": "password123",
  "username": "azureuser"
}'
```

### Test Login
```bash
curl --location --request POST 'http://vigilanteye-app.eastus.azurecontainer.io:8000/api/auth/login' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "azure-test@example.com",
  "password": "password123"
}'
```

### Test Web Pages
- Homepage: http://vigilanteye-app.eastus.azurecontainer.io:8000
- Login: http://vigilanteye-app.eastus.azurecontainer.io:8000/login
- Register: http://vigilanteye-app.eastus.azurecontainer.io:8000/register

## 🔍 Troubleshooting

### Issue: Templates not found
**Solution**: Ensure `app/templates` directory exists with all HTML files

### Issue: Static files not loading
**Solution**: Check that `app/static/css/style.css` and `app/static/js/script.js` exist

### Issue: Database connection error
**Solution**: 
1. Check DATABASE_URL environment variable
2. Ensure SSL parameters are included for Azure MySQL
3. Verify database credentials

### Issue: Session not working
**Solution**: 
1. Set SECRET_KEY environment variable
2. Clear browser cookies
3. Restart the application

### Issue: 404 on routes
**Solution**: 
1. Check that blueprints are registered in `app/__init__.py`
2. Verify route names in templates match controller routes

## 📋 Checklist

Before deploying to production:

- [ ] All environment variables set
- [ ] Database migrations run
- [ ] SSL configured for MySQL connection
- [ ] Static files accessible
- [ ] Templates rendering correctly
- [ ] Authentication working
- [ ] Session management working
- [ ] API endpoints responding
- [ ] Forms validating properly
- [ ] Error handling in place

## 🔑 Default Test Credentials

For testing, you can create a user with:
- **Username**: `admin`
- **Email**: `admin@vigilanteye.com`
- **Password**: `Admin123!@#`

## 📊 Monitoring

### View Logs
```bash
# Azure Container logs
az container logs --resource-group vigilanteye-docker-rg --name vigilanteye-app

# Follow logs in real-time
az container logs --resource-group vigilanteye-docker-rg --name vigilanteye-app --follow
```

### Check Container Status
```bash
az container show --resource-group vigilanteye-docker-rg --name vigilanteye-app \
  --query "{FQDN:ipAddress.fqdn, IP:ipAddress.ip, State:instanceView.state}"
```

## 🎯 Next Steps

1. ✅ Test all authentication flows
2. ✅ Verify dashboard loads
3. ⏳ Add real camera feeds
4. ⏳ Implement project management UI
5. ⏳ Add video player functionality
6. ⏳ Create alert configuration pages

## 📝 Notes

- Sessions are stored in Flask's default session management (server-side)
- JWT tokens are used for API authentication
- Password hashing uses bcrypt via Werkzeug
- All passwords must be at least 6 characters

## 🆘 Need Help?

1. Check FRONTEND_INTEGRATION.md for detailed information
2. Review DEPLOYMENT_GUIDE.md for deployment issues
3. Check application logs for errors
4. Verify environment variables are set correctly

---

**Happy Testing! 🎉**
