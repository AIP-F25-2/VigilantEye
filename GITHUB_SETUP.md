# GitHub CI/CD Setup Guide

## 🎯 Step-by-Step Setup

### Step 1: Create GitHub Repository

1. Go to GitHub.com
2. Click "New Repository"
3. Name: `VigilantEye` or your preferred name
4. Make it Private (recommended)
5. Don't initialize with README (we already have one)

### Step 2: Initialize Git (if not done)

```bash
git init
git add .
git commit -m "Initial commit with CI/CD pipeline"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/VigilantEye.git
git push -u origin main
```

### Step 3: Configure GitHub Secrets

Go to: `Repository → Settings → Secrets and variables → Actions → New repository secret`

Add these secrets:

#### Azure Secrets
```
Name: ACR_NAME
Value: vigilanteyeacr

Name: ACR_LOGIN_SERVER
Value: vigilanteyeacr.azurecr.io

Name: ACR_USERNAME
Value: vigilanteyeacr

Name: ACR_PASSWORD
Value: <Get from Azure - see below>

Name: AZURE_CREDENTIALS
Value: <Service Principal JSON - see below>
```

#### Application Secrets
```
Name: SECRET_KEY
Value: your-secret-key-here

Name: JWT_SECRET_KEY  
Value: jwt-secret-string

Name: DATABASE_URL
Value: mysql+pymysql://vigilanteye:YourPassword123%21@vigilanteye-mysql.mysql.database.azure.com:3306/flaskapi?ssl_ca=/etc/ssl/certs/ca-certificates.crt
```

#### Staging Secrets (Optional)
```
Name: STAGING_SECRET_KEY
Value: staging-secret-key

Name: STAGING_JWT_SECRET_KEY
Value: staging-jwt-secret

Name: STAGING_DATABASE_URL
Value: <staging database URL>
```

#### Airflow Secrets (For integration)
```
Name: AIRFLOW_URL
Value: http://your-airflow-server:8080

Name: AIRFLOW_USERNAME
Value: admin

Name: AIRFLOW_PASSWORD
Value: admin123
```

### Step 4: Get Azure Credentials

#### Get ACR Password
```powershell
az acr credential show --name vigilanteyeacr --query "passwords[0].value" -o tsv
```

#### Create Service Principal
```powershell
az ad sp create-for-rbac `
  --name "vigilanteye-github-actions" `
  --role contributor `
  --scopes /subscriptions/0d5e1028-f327-4038-b255-9d4ef2f80895/resourceGroups/vigilanteye-docker-rg `
  --sdk-auth
```

Copy the entire JSON output to `AZURE_CREDENTIALS` secret:
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx",
  ...
}
```

### Step 5: Protect Branches

Go to: `Repository → Settings → Branches → Add branch protection rule`

**For `main` branch:**
- ✅ Require a pull request before merging
- ✅ Require status checks to pass
  - Select: `test`, `lint`, `security`
- ✅ Require branches to be up to date
- ✅ Include administrators

**For `develop` branch:**
- ✅ Require pull request reviews: 1
- ✅ Require status checks to pass

### Step 6: Test the Pipeline

1. **Create a test change:**
   ```bash
   git checkout -b feature/test-cicd
   echo "# Test" >> README.md
   git add README.md
   git commit -m "Test CI/CD pipeline"
   git push origin feature/test-cicd
   ```

2. **Create Pull Request:**
   - Go to GitHub
   - Click "Compare & pull request"
   - Wait for checks to complete

3. **Merge to develop** (staging deployment)

4. **Merge to main** (production deployment)

## 🔄 CI/CD Workflow Overview

### On Pull Request
```
PR Created → PR Checks Workflow
  ├─ Code Linting (Black, isort, flake8)
  ├─ Security Scan (Trivy)
  └─ Unit Tests with Coverage
```

### On Push to Develop
```
Push to develop → Staging Deployment
  ├─ Build Docker Image
  ├─ Push to ACR (tag: staging)
  ├─ Deploy to Staging Container App
  └─ Run Health Checks
```

### On Push to Main
```
Push to main → Production Deployment
  ├─ Run All Tests
  ├─ Build Docker Image
  ├─ Push to ACR (tag: latest)
  ├─ Deploy to Production Container App
  ├─ Run Database Migrations
  ├─ Health Checks
  └─ Trigger Airflow DAGs
```

## 📊 Monitoring CI/CD

### GitHub Actions Dashboard
- Go to `Actions` tab in your repository
- See all workflow runs
- Click on any run to see details
- Download artifacts if needed

### Deployment Status
- Check `Environments` tab
- See deployment history
- View environment URLs

### Notifications
- Configure in `.github/workflows/*.yml`
- Email notifications on failure
- Slack integration (optional)

## 🧪 Local Testing

### Test Workflows Locally (Optional)
```bash
# Install nektos/act
https://github.com/nektos/act

# Run workflow locally
act push -j test

# Run specific job
act -j build --secret-file .env.secrets
```

### Manual Deployment Test
```bash
# Trigger workflow manually via GitHub CLI
gh workflow run main.yml

# Or via web interface
# Go to Actions → Select workflow → Run workflow
```

## 🔐 Security Best Practices

1. **Never commit secrets** to repository
2. **Use GitHub Secrets** for sensitive data
3. **Rotate credentials** regularly
4. **Enable branch protection**
5. **Require code reviews**
6. **Scan for vulnerabilities** (Trivy in pipeline)

## 📝 Customization

### Add New Workflow

Create `.github/workflows/your-workflow.yml`:
```yaml
name: Your Custom Workflow
on: [push]
jobs:
  your-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Your step
        run: echo "Hello"
```

### Add Secrets
```bash
# Via GitHub CLI
gh secret set SECRET_NAME --body "secret-value"

# Or via web interface
Settings → Secrets and variables → Actions → New secret
```

## ✅ Checklist

Before going live:

- [ ] GitHub repository created
- [ ] All secrets configured in GitHub
- [ ] Azure service principal created
- [ ] Branch protection rules set
- [ ] Test workflow runs successfully
- [ ] Staging environment tested
- [ ] Production deployment verified
- [ ] Airflow DAGs working
- [ ] Monitoring configured

## 🆘 Troubleshooting

### Workflow Not Triggering
- Check branch names match (main vs master)
- Verify push events configured
- Check repository permissions

### Deployment Failing
- Verify all secrets are set
- Check Azure credentials are valid
- Review workflow logs in GitHub

### Cannot Push to ACR
- Check ACR_PASSWORD is correct
- Verify ACR_USERNAME matches
- Ensure service principal has permissions

---

**Next Step**: Set up your GitHub repository and configure secrets!
