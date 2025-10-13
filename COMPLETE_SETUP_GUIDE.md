# 🚀 Complete Setup Guide - VIGILANTEye CI/CD with Airflow

## 🎯 What You Get

✅ **GitHub Actions CI/CD Pipeline** - Automated testing & deployment  
✅ **Apache Airflow** - Workflow orchestration  
✅ **HTTPS Enabled** - Secure production deployment  
✅ **Auto-scaling** - Handle traffic spikes  
✅ **Monitoring** - Application Insights & Airflow dashboard  

## 📋 Prerequisites

- ✅ GitHub account
- ✅ Azure subscription
- ✅ Docker Desktop installed
- ✅ Git installed
- ✅ Azure CLI installed
- ✅ GitHub CLI (optional but recommended)

## 🔥 Quick Start (Complete Setup in 15 Minutes)

### Step 1: Push to GitHub (2 minutes)

```bash
# Initialize git (if not done)
git init
git add .
git commit -m "Initial commit with CI/CD pipeline"

# Create GitHub repo and push
gh repo create VigilantEye --private --source=. --remote=origin --push

# Or manually:
# 1. Create repo on GitHub.com
# 2. git remote add origin https://github.com/YOUR_USERNAME/VigilantEye.git
# 3. git push -u origin main
```

### Step 2: Configure GitHub Secrets (5 minutes)

**Option A: Automated (Recommended)**
```powershell
.\setup-github-secrets.ps1
```

**Option B: Manual**
Follow instructions in `GITHUB_SETUP.md`

### Step 3: Test CI/CD Pipeline (3 minutes)

```bash
# Create test branch
git checkout -b feature/test-pipeline

# Make a small change
echo "# Test" >> README.md

# Push and create PR
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin feature/test-pipeline

# Create PR on GitHub
gh pr create --title "Test CI/CD" --body "Testing automated pipeline"

# Watch the magic happen! ✨
# GitHub Actions will automatically:
# - Run tests
# - Lint code
# - Security scan
```

### Step 4: Start Airflow (5 minutes)

```powershell
# Start Airflow
.\start-airflow.ps1

# Access at: http://localhost:8080
# Username: admin
# Password: admin123
```

## 📊 What's Running

After setup, you'll have:

### Production (Azure Container Apps)
- **URL**: https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io
- **Resources**: 2 CPU, 4GB RAM
- **Auto-scaling**: 1-3 replicas
- **Protocol**: HTTPS (free SSL)

### Development (Local Docker)
- **App**: http://localhost:8000
- **Airflow**: http://localhost:8080
- **phpMyAdmin**: http://localhost:8080 (if using docker-compose.yml)

## 🎨 Available Workflows

### GitHub Actions Workflows

1. **main.yml** - Main CI/CD pipeline
   - Triggers: Push to main/develop
   - Jobs: Test → Build → Deploy → Verify → Trigger Airflow

2. **pr-checks.yml** - Pull request checks
   - Triggers: Pull requests
   - Jobs: Lint → Security → Test

3. **deploy-staging.yml** - Staging deployment
   - Triggers: Push to develop
   - Jobs: Build → Deploy to staging

### Airflow DAGs

1. **video_processing_dag.py** - Hourly video processing
2. **analytics_dag.py** - Daily analytics (2 AM)
3. **database_maintenance_dag.py** - Daily cleanup (3 AM)

## 🔄 Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes
# ... code ...

# 3. Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# 4. Create PR
gh pr create

# 5. Wait for CI checks ✅

# 6. Merge to develop (auto-deploys to staging)
gh pr merge --auto --squash

# 7. Test on staging
# https://vigilanteye-app-staging...

# 8. Merge develop → main (auto-deploys to production)
git checkout main
git merge develop
git push origin main

# 9. Monitor deployment
# GitHub Actions → View workflow run
```

## 📁 Files Created

### CI/CD Files
```
.github/workflows/
├── main.yml                # Main CI/CD pipeline
├── pr-checks.yml          # PR validation
└── deploy-staging.yml     # Staging deployment
```

### Airflow Files
```
airflow/
├── dags/
│   ├── video_processing_dag.py     # Video processing
│   ├── analytics_dag.py            # Analytics generation
│   └── database_maintenance_dag.py # DB maintenance
├── logs/                   # Airflow logs
└── plugins/                # Custom operators
```

### Docker Files
```
docker-compose.yml          # Local development
docker-compose.airflow.yml  # Airflow services
Dockerfile                  # Application container
```

### Scripts
```
setup-github-secrets.ps1    # Configure GitHub secrets
start-airflow.ps1          # Start Airflow
deploy.ps1                 # Manual Azure deployment
test-local.ps1             # Local Docker testing
```

### Documentation
```
README.md                   # This file
CICD_AIRFLOW_GUIDE.md      # Detailed CI/CD guide
GITHUB_SETUP.md            # GitHub configuration
DEPLOYMENT_GUIDE.md        # Azure deployment
HTTPS_SETUP.md             # HTTPS options
ROUTES_STRUCTURE.md        # API documentation
```

## ✅ Verification Checklist

### GitHub Setup
- [ ] Repository created on GitHub
- [ ] Code pushed to repository
- [ ] All secrets configured
- [ ] Branch protection rules set
- [ ] First workflow run successful

### Azure Deployment
- [ ] Container App running with HTTPS
- [ ] Health endpoint responding
- [ ] Can register/login users
- [ ] Dashboard accessible
- [ ] Database connected

### Airflow Setup
- [ ] Airflow running locally
- [ ] Can access Airflow UI (localhost:8080)
- [ ] DAGs visible in UI
- [ ] Can trigger DAGs manually
- [ ] Logs visible for task runs

## 🔍 Monitoring & Debugging

### GitHub Actions
```bash
# View workflow runs
gh run list

# View specific run
gh run view <run-id>

# Watch live
gh run watch
```

### Azure Container Apps
```bash
# View logs
az containerapp logs show \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg \
  --follow

# Check status
az containerapp show \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg
```

### Airflow
```bash
# View logs
docker-compose -f docker-compose.airflow.yml logs -f

# Check DAG status
docker-compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags list

# Trigger DAG
docker-compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags trigger video_processing_pipeline
```

## 🎓 Learning Resources

- [GitHub Actions Tutorial](https://docs.github.com/en/actions/learn-github-actions)
- [Airflow Tutorial](https://airflow.apache.org/docs/apache-airflow/stable/tutorial.html)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Flask Best Practices](https://flask.palletsprojects.com/en/latest/)

## 🐛 Common Issues

### Issue: GitHub Actions failing
**Solution**: Check GitHub Secrets are all set correctly

### Issue: Airflow DAGs not appearing
**Solution**: 
```bash
docker-compose -f docker-compose.airflow.yml restart airflow-scheduler
```

### Issue: Container App not accessible
**Solution**: Wait 2-3 minutes for DNS propagation

## 🎯 Production Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Set strong SECRET_KEY
- [ ] Configure email notifications
- [ ] Set up monitoring alerts
- [ ] Configure auto-scaling rules
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Train team on Airflow

## 💡 Tips

1. **Use staging environment** for testing changes
2. **Monitor Airflow DAG runs** regularly
3. **Set up Slack notifications** for critical failures
4. **Review analytics daily** from Airflow reports
5. **Keep Docker images small** for faster deployments

## 🚀 You're All Set!

Your VIGILANTEye system now has:
- ✅ Automated CI/CD pipeline
- ✅ Workflow orchestration with Airflow
- ✅ HTTPS security
- ✅ Auto-scaling
- ✅ Complete monitoring

**Happy monitoring! 🎉**

---

**Created**: October 9, 2025  
**Status**: ✅ Production Ready
