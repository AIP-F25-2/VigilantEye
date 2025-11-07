@echo off
REM Fix corrupted .env file by restoring from env.example

echo ====================================
echo 🔧 Fixing .env file
echo ====================================

cd /d "%~dp0"

if not exist "env.example" (
    echo ❌ env.example not found!
    pause
    exit /b 1
)

if exist ".env" (
    echo Backing up current .env to .env.backup...
    copy /Y .env .env.backup >nul 2>&1
    echo ✅ Backup created: .env.backup
)

echo Copying env.example to .env...
copy /Y env.example .env >nul 2>&1

if exist ".env" (
    echo ✅ .env file restored successfully!
    echo.
    echo Please edit .env with your configuration:
    echo   - Database credentials (DB_USER, DB_PASSWORD, DB_NAME)
    echo   - JWT secret keys (JWT_SECRET_KEY)
    echo   - API keys (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN)
    echo.
) else (
    echo ❌ Failed to create .env file!
    pause
    exit /b 1
)

pause

