# Testing CI/CD Pipeline - dev_pipline_test Branch

## 🎯 Goal
Test the GitHub Actions CI/CD pipeline using your `dev_pipline_test` branch.

## 📋 Prerequisites

1. **Install Git** (if not already installed)
   - Download: https://git-scm.com/download/win
   - During installation, select "Git from the command line and also from 3rd-party software"
   - Restart PowerShell after installation

2. **GitHub Account**
   - Have your GitHub credentials ready

3. **Current Branch**
   - You're on: `dev_pipline_test`

## 🚀 Step-by-Step Testing

### Step 1: Verify Git Installation

```powershell
# Restart PowerShell, then test
git --version

# Should show: git version 2.x.x
```

### Step 2: Check Current Status

```powershell
# View current branch
git branch

# Should show: * dev_pipline_test

# Check what files have changed
git status
```

### Step 3: Commit All Changes

```powershell
# Add all files
git add .

# Commit with a message
git commit -m "Add CI/CD pipeline with Airflow integration"

# View commit
git log --oneline -1
```

### Step 4: Push to GitHub

```powershell
# If first time pushing this branch
git push -u origin dev_pipline_test

# Or if already exists
git push origin dev_pipline_test
```

### Step 5: Create Pull Request

**Option A: Using GitHub CLI (if installed)**
```powershell
gh pr create --title "Add CI/CD Pipeline & Airflow" --body "Testing automated CI/CD pipeline" --base main
```

**Option B: Via GitHub Website**
1. Go to your GitHub repository
2. Click "Compare & pull request" (will appear after push)
3. Title: "Add CI/CD Pipeline & Airflow"
4. Description: "Testing CI/CD pipeline with Airflow integration"
5. Base: `main` ← Compare: `dev_pipline_test`
6. Click "Create pull request"

### Step 6: Watch CI/CD in Action

Once PR is created, GitHub Actions will automatically:

1. ✅ **Code Linting** (Black, isort, flake8)
2. ✅ **Security Scan** (Trivy vulnerability scanning)
3. ✅ **Unit Tests** (pytest with coverage)

**View progress:**
- Go to `Actions` tab in GitHub
- Click on the running workflow
- Watch each job execute

### Step 7: Review & Merge

Once all checks pass:

```powershell
# Option A: Via GitHub CLI
gh pr merge --auto --squash

# Option B: Via GitHub Website
# Click "Merge pull request" button
```

After merging to `main`, the **deployment pipeline** runs:
1. ✅ Build Docker image
2. ✅ Push to Azure Container Registry
3. ✅ Deploy to Azure Container Apps (HTTPS)
4. ✅ Run database migrations
5. ✅ Health checks
6. ✅ Trigger Airflow DAGs

## 📊 What Each Workflow Does

### PR Checks Workflow (`pr-checks.yml`)
```
Pull Request Created
  ↓
├─ Lint (Check code formatting)
├─ Security (Scan for vulnerabilities)
└─ Test (Run unit tests)
  ↓
All checks pass ✅
```

### Main CI/CD Workflow (`main.yml`)
```
Push to Main
  ↓
├─ Test (pytest with coverage)
├─ Build (Docker image)
├─ Deploy (to Azure Container Apps)
├─ Verify (health checks)
└─ Trigger Airflow (start DAGs)
  ↓
Deployment Complete ✅
```

### Staging Workflow (`deploy-staging.yml`)
```
Push to Develop
  ↓
├─ Build (Docker with 'staging' tag)
└─ Deploy (to staging environment)
  ↓
Staging Ready for Testing ✅
```

## 🔍 Monitoring Pipeline Execution

### View on GitHub
1. Go to `Actions` tab
2. See all workflow runs
3. Click any run for details
4. View logs for each job

### View Deployment Status
1. Go to `Environments` tab
2. See deployment history
3. Click environment for details

### Check Production
```powershell
# Test health endpoint
Invoke-RestMethod -Uri "https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io/health"

# Open in browser
start https://vigilanteye-app.politepond-67bfac4f.eastus.azurecontainerapps.io
```

## 🎨 Airflow Integration

After successful deployment, Airflow DAGs are automatically triggered.

### View Airflow Execution

```powershell
# Start Airflow locally
.\start-airflow.ps1

# Access at http://localhost:8080
# Username: admin
# Password: admin123
```

**Available DAGs:**
1. **video_processing_pipeline** - Runs hourly
2. **analytics_pipeline** - Runs daily at 2 AM
3. **database_maintenance** - Runs daily at 3 AM

## 🧪 Test Scenarios

### Scenario 1: Test Linting
```powershell
# Create a file with bad formatting
echo "def test( ):pass" > app/test_bad.py

# Commit and push
git add app/test_bad.py
git commit -m "Test linting"
git push origin dev_pipline_test

# PR checks will fail ❌ (intentional)
# Fix the code, push again, checks pass ✅
```

### Scenario 2: Test Automated Deployment
```powershell
# Make a simple change
echo "# Updated" >> README.md

# Commit and push to main
git add README.md
git commit -m "Update README"
git push origin main

# Watch automatic deployment in Actions tab
```

### Scenario 3: Test Airflow DAG
```powershell
# Start Airflow
.\start-airflow.ps1

# Access UI: http://localhost:8080
# 1. Click on "video_processing_pipeline"
# 2. Toggle to "Active"
# 3. Click "Trigger DAG"
# 4. Watch execution in Graph view
```

## 🐛 Troubleshooting

### Issue: Git not found
**Solution:**
```powershell
# Install Git
winget install --id Git.Git -e --source winget

# Or download from
# https://git-scm.com/download/win

# Restart PowerShell
```

### Issue: GitHub Actions not running
**Solution:**
- Check GitHub Secrets are configured
- Verify workflow files exist in `.github/workflows/`
- Check branch names match (main, develop, etc.)

### Issue: Deployment failing
**Solution:**
```powershell
# Check Azure credentials
az account show

# Verify ACR access
az acr login --name vigilanteyeacr

# Check Container App status
az containerapp show --name vigilanteye-app --resource-group vigilanteye-docker-rg
```

### Issue: Airflow DAG not appearing
**Solution:**
```powershell
# Restart Airflow scheduler
docker-compose -f docker-compose.airflow.yml restart airflow-scheduler

# Check logs
docker-compose -f docker-compose.airflow.yml logs -f airflow-scheduler
```

## 📝 Git Commands Cheat Sheet

```powershell
# View current branch
git branch

# Switch branch
git checkout dev_pipline_test

# Create new branch
git checkout -b feature/new-feature

# View changes
git status
git diff

# Commit changes
git add .
git commit -m "Your message"

# Push changes
git push origin dev_pipline_test

# Pull latest
git pull origin main

# Merge main into your branch
git merge main
```

## ✅ Success Criteria

Your CI/CD pipeline is working when:

- [ ] PR checks run automatically on pull requests
- [ ] All checks pass (lint, security, test)
- [ ] Deployment runs on merge to main
- [ ] Application updates without downtime
- [ ] Health check passes after deployment
- [ ] Airflow DAGs trigger successfully
- [ ] Can view execution logs in both GitHub and Airflow

## 🎯 Next Actions for Your Branch

1. **Commit current changes:**
   ```powershell
   git add .
   git commit -m "Complete CI/CD and Airflow setup"
   ```

2. **Push to GitHub:**
   ```powershell
   git push origin dev_pipline_test
   ```

3. **Create PR:**
   - Go to GitHub repository
   - Click "Compare & pull request"
   - Review changes
   - Create pull request

4. **Watch Pipeline Run:**
   - Go to Actions tab
   - See PR checks running
   - Wait for ✅ All checks passed

5. **Merge to Main:**
   - Merge the PR
   - Watch production deployment
   - Verify at HTTPS URL

## 📞 Need Help?

If you encounter issues:
1. Check `COMPLETE_SETUP_GUIDE.md`
2. Review error logs in GitHub Actions
3. Check Azure Container Apps logs
4. Review Airflow logs if workflow-related

---

**Your Branch**: dev_pipline_test  
**Target**: Merge to main  
**Result**: Automated deployment to production with HTTPS! 🚀
