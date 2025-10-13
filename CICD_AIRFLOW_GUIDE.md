# CI/CD Pipeline with GitHub Actions & Apache Airflow

## 🎯 Overview

This guide sets up a complete CI/CD pipeline for VIGILANTEye using:
- **GitHub Actions** - Automated testing, building, and deployment
- **Apache Airflow** - Workflow orchestration and scheduled tasks

## 📋 Architecture

```
┌─────────────────┐
│  GitHub Repo    │
│  (Code Push)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │
│ - Run Tests     │
│ - Build Docker  │
│ - Push to ACR   │
│ - Deploy to ACA │
└────────┬────────┘
         │
         ▼
┌─────────────────┐        ┌──────────────────┐
│ Azure Container │◄───────┤ Apache Airflow   │
│ Apps (HTTPS)    │        │ - Video Process  │
│ VIGILANTEye App │        │ - Analytics      │
└─────────────────┘        │ - Maintenance    │
                           └──────────────────┘
```

## 🚀 Part 1: GitHub Actions CI/CD

### Workflows Created

#### 1. **Main CI/CD Pipeline** (`.github/workflows/main.yml`)
Triggers on: Push to `main` or `develop`

**Jobs:**
1. **Test** - Run unit tests and linting
2. **Build** - Build Docker image and push to ACR
3. **Deploy** - Deploy to Azure Container Apps
4. **Verify** - Health checks and smoke tests
5. **Trigger Airflow** - Kick off Airflow DAGs

#### 2. **PR Checks** (`.github/workflows/pr-checks.yml`)
Triggers on: Pull requests

**Jobs:**
1. **Lint** - Code quality (Black, isort, flake8)
2. **Security** - Vulnerability scanning (Trivy)
3. **Test** - Unit tests with coverage

#### 3. **Staging Deployment** (`.github/workflows/deploy-staging.yml`)
Triggers on: Push to `develop`

**Jobs:**
1. Deploy to staging environment for testing

### Required GitHub Secrets

Set these in: `GitHub Repo → Settings → Secrets and variables → Actions`

```
ACR_NAME=vigilanteyeacr
ACR_LOGIN_SERVER=vigilanteyeacr.azurecr.io
ACR_USERNAME=vigilanteyeacr
ACR_PASSWORD=<from Azure>
AZURE_CREDENTIALS=<Service Principal JSON>
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-string
DATABASE_URL=mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt
STAGING_SECRET_KEY=staging-secret-key
STAGING_JWT_SECRET_KEY=staging-jwt-key
STAGING_DATABASE_URL=<staging database URL>
AIRFLOW_URL=http://your-airflow-url:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin123
```

### How to Get Azure Credentials

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "vigilanteye-github-actions" \
  --role contributor \
  --scopes /subscriptions/0d5e1028-f327-4038-b255-9d4ef2f80895/resourceGroups/vigilanteye-docker-rg \
  --sdk-auth

# Copy the JSON output to AZURE_CREDENTIALS secret
```

### Get ACR Password

```bash
az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv
```

## 🌊 Part 2: Apache Airflow Setup

### DAGs Created

#### 1. **Video Processing Pipeline** (`video_processing_dag.py`)
- **Schedule**: Every hour
- **Tasks**:
  1. Fetch pending videos
  2. Process videos (AI analysis)
  3. Generate thumbnails
  4. Update analytics
  5. Cleanup temp files

#### 2. **Analytics Pipeline** (`analytics_dag.py`)
- **Schedule**: Daily at 2 AM
- **Tasks**:
  1. Extract daily metrics
  2. Calculate trends
  3. Generate AI insights
  4. Save to database
  5. Send daily report

#### 3. **Database Maintenance** (`database_maintenance_dag.py`)
- **Schedule**: Daily at 3 AM
- **Tasks**:
  1. Cleanup old recordings (>30 days)
  2. Archive old videos (>90 days)
  3. Optimize database tables
  4. Generate maintenance report

### Start Airflow Locally

```bash
# Start all services
docker-compose -f docker-compose.airflow.yml up -d

# Access Airflow UI
http://localhost:8080

# Login credentials
Username: admin
Password: admin123
```

### Airflow Commands

```bash
# View logs
docker-compose -f docker-compose.airflow.yml logs -f airflow-webserver

# Stop Airflow
docker-compose -f docker-compose.airflow.yml down

# Restart Airflow
docker-compose -f docker-compose.airflow.yml restart

# Trigger DAG manually
docker-compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags trigger video_processing_pipeline
```

## 🔄 CI/CD Workflow

### Development Flow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes & Commit**
   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

3. **Create Pull Request**
   - Triggers PR checks (lint, security, tests)
   - Code review

4. **Merge to Develop**
   - Auto-deploys to staging
   - Run integration tests

5. **Merge to Main**
   - Auto-deploys to production
   - Triggers Airflow workflows
   - Sends notifications

### Deployment Process

```
Code Push → GitHub Actions
    ↓
Run Tests
    ↓
Build Docker Image
    ↓
Push to Azure Container Registry
    ↓
Deploy to Azure Container Apps (Zero Downtime)
    ↓
Run Database Migrations
    ↓
Health Checks
    ↓
Trigger Airflow DAGs
    ↓
✅ Deployment Complete
```

## 📊 Monitoring & Observability

### GitHub Actions
- View workflow runs: `Actions` tab in GitHub
- Check logs for each job
- See deployment status

### Azure Container Apps
```bash
# View logs
az containerapp logs show \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg \
  --follow

# View metrics
az containerapp show \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg
```

### Airflow Dashboard
- **URL**: http://localhost:8080 (local) or your deployed Airflow URL
- **Monitor**: DAG runs, task status, logs
- **Alerts**: Failed task notifications

## 🔧 Configuration

### Environment Variables (Production)

Set in Azure Container Apps:
```bash
FLASK_ENV=production
SECRET_KEY=<strong-secret-key>
JWT_SECRET_KEY=<jwt-secret>
DATABASE_URL=<mysql-connection-string>
```

### Airflow Variables

Set in Airflow UI → Admin → Variables:
```
vigilanteye_api_url=https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io
vigilanteye_api_key=<your-api-key>
alert_email=admin@vigilanteye.com
retention_days=30
archive_days=90
```

## 🧪 Testing the CI/CD Pipeline

### 1. Test GitHub Actions Locally (Act)

```bash
# Install act
https://github.com/nektos/act

# Test workflow
act push -j test
```

### 2. Test Deployment Manually

```bash
# Trigger workflow manually
gh workflow run main.yml

# Or push to trigger
git push origin main
```

### 3. Test Airflow DAGs

```bash
# Test video processing DAG
airflow dags test video_processing_pipeline 2025-10-09

# Test analytics DAG
airflow dags test analytics_pipeline 2025-10-09
```

## 📝 Best Practices

### Git Workflow
1. **Feature branches** from `develop`
2. **PR reviews** before merging
3. **Protected branches** (main, develop)
4. **Semantic versioning** tags

### Docker
1. **Multi-stage builds** for smaller images
2. **Layer caching** for faster builds
3. **Security scanning** with Trivy
4. **Non-root user** in container

### Airflow
1. **Idempotent tasks** - safe to retry
2. **Error handling** - graceful failures
3. **Monitoring** - email on failure
4. **Documentation** - clear DAG descriptions

## 🐛 Troubleshooting

### GitHub Actions Failing

**Check logs:**
- Go to Actions tab
- Click on failed workflow
- Review job logs

**Common issues:**
- Missing secrets
- Invalid credentials
- Network timeout

### Airflow DAG Failing

**Check logs:**
```bash
docker-compose -f docker-compose.airflow.yml logs -f airflow-scheduler
```

**Common issues:**
- API endpoint not accessible
- Invalid authentication
- Database connection issues

### Deployment Issues

**Rollback:**
```bash
# List revisions
az containerapp revision list \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg

# Activate previous revision
az containerapp revision activate \
  --resource-group vigilanteye-docker-rg \
  --name vigilanteye-app \
  --revision <previous-revision-name>
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Container Apps CI/CD](https://learn.microsoft.com/azure/container-apps/github-actions)
- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🎯 Next Steps

1. ✅ Set up GitHub Secrets
2. ✅ Push code to GitHub
3. ✅ Watch CI/CD pipeline run
4. ✅ Start Airflow for workflow orchestration
5. ✅ Monitor deployments and DAG runs

---

**Created**: October 9, 2025  
**Status**: ✅ Ready for Implementation
