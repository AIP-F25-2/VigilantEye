# ⚡ VIGILANTEye Quick Start Guide

Get up and running with VIGILANTEye in minutes!

## 🚀 Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/AIP-F25-2/VigilantEye.git
cd VigilantEye

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
# Create .env file or export:
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/flaskapi"
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="your-jwt-secret"

# 5. Run database migrations
flask db upgrade

# 6. Start the application
python run.py
```

## 🌐 Access the Application

- **Homepage**: http://localhost:8000/
- **Login**: http://localhost:8000/login
- **Dashboard**: http://localhost:8000/dashboard
- **API Health**: http://localhost:8000/health

## 📦 Docker Quick Start

```bash
# Start all services (MySQL + App)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔑 Default Credentials

Create your first user by registering at `/signup` or via API:

```bash
POST /api/auth/register
{
  "email": "admin@example.com",
  "password": "password123",
  "username": "admin"
}
```

## 📚 Next Steps

- Read [README.md](README.md) for full documentation
- Check [COLLABORATION_GUIDE.md](COLLABORATION_GUIDE.md) for team workflow
- Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for project overview

## 🆘 Troubleshooting

**Database connection error?**
- Check DATABASE_URL environment variable
- Ensure MySQL is running
- Verify credentials

**Import errors?**
- Activate virtual environment
- Run `pip install -r requirements.txt`
- Check Python version (3.11+)

**Port already in use?**
- Change port in `run.py`: `app.run(port=8001)`
- Or stop the process using port 8000

---

**Need help?** Open an issue on [GitHub](https://github.com/AIP-F25-2/VigilantEye/issues)

