# Database Migration Solution

## Problem
The `az containerapp exec` command is failing with a websocket error, preventing manual migration execution.

## ✅ Solution 1: Automatic Migrations on Startup (IMPLEMENTED)

I've updated `run.py` to automatically run database migrations when the application starts. This means:

1. **Current Status**: The code has been updated
2. **Next Step**: Rebuild and redeploy the image (currently running in background)
3. **Result**: Migrations will run automatically when the container starts

### What Changed
- Added automatic migration execution in `run.py`
- Migrations run in a try-catch block (won't crash app if they fail)
- Logs migration status for debugging

### To Apply
The rebuild is currently running. Once complete:
```powershell
az containerapp update `
  --name vigilanteye-app `
  --resource-group vigilanteye-docker-rg `
  --image vigilanteyeacr.azurecr.io/vigilanteye:latest
```

## Alternative Solutions

### Solution 2: Azure Portal Console
1. Go to Azure Portal
2. Navigate to: Container Apps → `vigilanteye-app`
3. Click on "Console" or "Exec" tab
4. Run: `flask db upgrade`

### Solution 3: Check Current Migration Status
You can check if migrations have already run by checking the logs:
```powershell
az containerapp logs show `
  --name vigilanteye-app `
  --resource-group vigilanteye-docker-rg `
  --follow
```

Look for messages like:
- "Running database migrations..."
- "Database migrations completed successfully"

### Solution 4: Manual SQL Execution
If you have access to the MySQL database directly, you can run the migration SQL manually by:
1. Connecting to `vigilanteye-mysql.mysql.database.azure.com`
2. Running the SQL from the migration files in `migrations/versions/`

## Current Build Status

The rebuild with auto-migration is running. Check status with:
```powershell
az acr task list-runs --registry vigilanteyeacr --output table --top 1
```

Wait until STATUS shows "Succeeded", then update the Container App.

## Verification

After deployment, check logs to verify migrations ran:
```powershell
az containerapp logs show `
  --name vigilanteye-app `
  --resource-group vigilanteye-docker-rg `
  --tail 50
```

You should see:
```
Running database migrations...
INFO [alembic.runtime.migration] Running upgrade ...
Database migrations completed successfully
```

## Migration Files

The following migrations should run:
1. `add_faceai_models` - Creates FaceAi tables
2. `add_face_identity_agent_models` - Creates CCTV/Identity Agent tables

These will create tables for:
- `face_detections`
- `demographics_analyses`
- `ambiguity_analyses`
- `face_encodings`
- `faceai_configurations`
- `person_identities`
- And other related tables

