# EYEQ Setup Guide

## 🚀 Quick Start (Demo Version)

The easiest way to get started is with the demo version that uses file-based storage instead of MySQL.

### 1. Run the Demo App
```bash
cd auth_app
python demo_app.py
```

### 2. Open Your Browser
- Go to: http://localhost:5000
- Test the registration and login functionality

## 🗄️ Full MySQL Version Setup

For production use with MySQL database:

### Prerequisites
- Python 3.7+
- MySQL 5.7+ or MySQL 8.0+
- pip (Python package manager)

### Step 1: Install Dependencies
```bash
cd auth_app
pip install -r requirements.txt
```

### Step 2: Configure MySQL
1. **Start MySQL service** on your system
2. **Update database credentials** in `config.py`:
   ```python
   class Config:
       MYSQL_HOST = 'localhost'        # Your MySQL host
       MYSQL_USER = 'root'             # Your MySQL username
       MYSQL_PASSWORD = 'your_password' # Your MySQL password
       MYSQL_DATABASE = 'auth_db'      # Database name
   ```

### Step 3: Initialize Database
```bash
python -c "from database import create_database, init_database; create_database(); init_database()"
```

### Step 4: Run the Application
```bash
python app.py
```

## 🔧 Troubleshooting

### MySQL Connection Issues
If you get MySQL connection errors:

1. **Check MySQL is running:**
   ```bash
   # Windows
   net start mysql
   
   # Linux/Mac
   sudo systemctl start mysql
   ```

2. **Verify credentials** in `config.py`

3. **Test connection manually:**
   ```bash
   python test_mysql.py
   ```

### Python Package Issues
If you get import errors:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install packages individually
pip install Flask
pip install bcrypt
pip install mysql-connector-python
pip install python-dotenv
```

### Port Already in Use
If port 5000 is busy:
```python
# In app.py, change the port
app.run(debug=True, host='0.0.0.0', port=5001)
```

## 📁 Project Structure

```
auth_app/
├── app.py              # Main Flask app (MySQL version)
├── demo_app.py         # Demo app (file-based storage)
├── config.py           # Configuration settings
├── database.py         # MySQL database functions
├── models.py           # User model and authentication
├── requirements.txt    # Python dependencies
├── test_mysql.py       # MySQL connection test
├── users.json          # Demo data storage (created automatically)
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
└── static/             # CSS and JavaScript
    ├── style.css
    └── script.js
```

## 🌟 Features

### Authentication Features
- ✅ User registration with validation
- ✅ Secure login with session management
- ✅ Password hashing with bcrypt
- ✅ Email format validation
- ✅ Username availability checking
- ✅ Real-time form validation
- ✅ Responsive design

### Security Features
- 🔒 Password hashing with salt
- 🛡️ SQL injection prevention
- 🔐 Session-based authentication
- ✅ Input validation and sanitization

### User Experience
- 📱 Mobile-responsive design
- ⚡ Real-time validation
- 🎨 Modern Bootstrap UI
- 🔄 Loading states and feedback

## 🧪 Testing the Application

### 1. Registration Test
1. Go to http://localhost:5000
2. Click "Sign Up"
3. Fill in the form:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `password123`
   - Confirm Password: `password123`
4. Click "Create Account"

### 2. Login Test
1. Use the credentials from registration
2. Click "Login"
3. Enter username and password
4. Verify you're redirected to dashboard

### 3. Logout Test
1. Click "Logout" in the navigation
2. Verify you're redirected to home page

## 🔄 Switching Between Versions

### Use Demo Version (File Storage)
```bash
python demo_app.py
```

### Use MySQL Version
```bash
python app.py
```

## 📝 API Endpoints

- `GET /` - Home page
- `GET /login` - Login page
- `POST /login` - Login handler
- `GET /signup` - Registration page
- `POST /signup` - Registration handler
- `GET /logout` - Logout handler
- `GET /api/check-username` - Check username availability
- `GET /api/check-email` - Check email availability

## 🚀 Production Deployment

For production deployment:

1. **Change secret key** in `config.py`
2. **Use environment variables** for database credentials
3. **Set up proper MySQL database** with restricted user
4. **Use a production WSGI server** like Gunicorn
5. **Set up reverse proxy** with Nginx
6. **Enable HTTPS** with SSL certificates

## 📞 Support

If you encounter issues:

1. Check this troubleshooting guide
2. Verify all dependencies are installed
3. Ensure MySQL is running (for MySQL version)
4. Check the console output for error messages
5. Test with the demo version first

## 🎯 Next Steps

After getting the basic authentication working:

1. Add email verification
2. Implement password reset functionality
3. Add user profile management
4. Implement role-based access control
5. Add logging and monitoring
6. Set up automated testing
