# 🔒 Security Setup Guide

## ⚠️ Important Security Notes

All sensitive credentials (database passwords, API keys, secrets) have been removed from the codebase and must be configured via environment variables or secrets management.

## 🔑 Required Environment Variables

### Database Configuration

**For Production:**
```bash
DATABASE_URL=mysql+pymysql://username:password@host:port/database
```

**For Local Development:**
- If `FLASK_ENV=development` and `DATABASE_URL` is not set, the app will use SQLite (with a warning)
- For MySQL, set `DATABASE_URL` explicitly

### Docker Compose Setup

1. **Create a `.env` file** in the project root:
```bash
# Copy the example file
cp .env.example .env
```

2. **Edit `.env`** and set your secure passwords:
```bash
MYSQL_DATABASE=flaskapi
MYSQL_USER=flaskuser
MYSQL_PASSWORD=your-secure-password-here
MYSQL_ROOT_PASSWORD=your-secure-root-password-here
DATABASE_URL=mysql+pymysql://flaskuser:your-secure-password-here@localhost:3306/flaskapi
```

3. **Start services:**
```bash
docker-compose up -d
```

**⚠️ Never commit `.env` to version control!** It's already in `.gitignore`.

### Azure Container Apps Setup

The `containerapp.json` file now uses Azure secrets instead of hardcoded values.

**To configure the database secret:**

1. **Create the secret in Azure:**
```bash
az containerapp secret set \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg \
  --secrets database-url="mysql+pymysql://user:password@host:port/database"
```

2. **Or use Azure Portal:**
   - Go to your Container App
   - Navigate to "Secrets" section
   - Add a new secret named `database-url` with your connection string

3. **Update other secrets as needed:**
```bash
az containerapp secret set \
  --name vigilanteye-app \
  --resource-group vigilanteye-docker-rg \
  --secrets \
    database-url="mysql+pymysql://..." \
    secret-key="your-secret-key" \
    jwt-secret-key="your-jwt-secret"
```

### Application Secrets

Set these environment variables for production:

```bash
SECRET_KEY=your-secret-key-here  # Generate a strong random key
JWT_SECRET_KEY=your-jwt-secret-here  # Generate a strong random key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret
```

**Generate secure secrets:**
```python
import secrets
print(secrets.token_urlsafe(32))  # For SECRET_KEY and JWT_SECRET_KEY
```

## ✅ Security Checklist

- [x] Removed hardcoded MySQL passwords from `config.py`
- [x] Removed hardcoded MySQL passwords from `docker-compose.yml`
- [x] Removed hardcoded MySQL passwords from `containerapp.json`
- [x] Created `.env.example` template
- [x] Created `docker-compose.example.yml` template
- [x] `.env` is in `.gitignore`
- [ ] Set up Azure secrets for production
- [ ] Generate and set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Rotate any previously exposed credentials
- [ ] Review and update Telegram bot token if it was exposed

## 🔄 Rotating Exposed Credentials

If credentials were previously committed to the repository:

1. **Change the database password:**
   ```sql
   ALTER USER 'flaskuser'@'%' IDENTIFIED BY 'new-secure-password';
   FLUSH PRIVILEGES;
   ```

2. **Update environment variables** with the new password

3. **Revoke and regenerate Telegram bot token** if it was exposed:
   - Go to [@BotFather](https://t.me/botfather) on Telegram
   - Use `/revoke` command
   - Generate a new token

4. **Review Git history** - Consider using `git filter-branch` or BFG Repo-Cleaner to remove sensitive data from history

## 📝 Notes

- Default values in `config.py` (like `'dev-secret-key'`) are **only for local development**
- Production deployments **must** set all environment variables
- The application will raise an error if `DATABASE_URL` is not set in production mode
- For local development, SQLite is used as a fallback (with a warning)

