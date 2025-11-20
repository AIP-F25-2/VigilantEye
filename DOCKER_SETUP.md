# Docker Setup Guide for VigilantEye

This guide will help you run VigilantEye using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start

1. **Clone the repository** (if you haven't already)

2. **Set up environment variables** (optional)
   
   Create a `.env` file in the root directory with your configuration:
   ```env
   # Flask Configuration
   SECRET_KEY=your-secret-key-here-change-in-production
   JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
   FLASK_ENV=production
   FLASK_DEBUG=0
   
   # Database Configuration
   DATABASE_URL=mysql+pymysql://flaskuser:flaskpass@db:3306/flaskapi
   
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
   TELEGRAM_WEBHOOK_SECRET=your-webhook-secret-here
   
   # Message Processing Configuration
   ESCALATE_AFTER_SECONDS=900
   CLOSE_AFTER_SECONDS=3600
   
   # Channel Configuration
   ALT_CHANNELS_FILE=alternate_channels.json
   DEFAULT_CHANNEL=your-default-channel-id
   ESCALATION_CHANNEL=your-escalation-channel-id
   ```

3. **Build and start the containers**
   ```bash
   docker-compose up -d
   ```

4. **Check the logs**
   ```bash
   docker-compose logs -f web
   ```

5. **Access the application**
   - Web Application: http://localhost:8000
   - phpMyAdmin: http://localhost:8080
   - MySQL: localhost:3306

## Services

The Docker Compose setup includes three services:

### 1. `web` - Flask Application
- **Port**: 8000
- **Image**: Built from local Dockerfile
- **Features**: 
  - Runs Flask application with Gunicorn
  - Automatically runs database migrations on startup
  - Includes all FaceAI dependencies (OpenCV, face-recognition, etc.)

### 2. `db` - MySQL Database
- **Port**: 3306
- **Image**: mysql:8.0
- **Database**: flaskapi
- **User**: flaskuser
- **Password**: flaskpass
- **Root Password**: rootpass

### 3. `phpmyadmin` - Database Management
- **Port**: 8080
- **Image**: phpmyadmin:latest
- **Access**: http://localhost:8080
- **Login**: root / rootpass

## Volumes

The following volumes are created for persistent data:
- `mysql_data`: MySQL database files
- `uploads_data`: User uploaded files
- `instance_data`: Application instance data (SQLite if used)
- `cctv_videos_data`: CCTV video files

## Common Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f db
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Run database migrations manually
```bash
docker-compose exec web flask db upgrade
```

### Access container shell
```bash
docker-compose exec web sh
```

### Stop and remove volumes (⚠️ deletes all data)
```bash
docker-compose down -v
```

## Environment Variables

You can set environment variables in two ways:

1. **Using `.env` file** (recommended)
   - Create a `.env` file in the root directory
   - Variables will be automatically loaded by docker-compose

2. **In docker-compose.yml**
   - Edit the `environment` section under the `web` service
   - Not recommended for sensitive data

## Production Deployment

For production deployment, consider:

1. **Change default passwords** in `docker-compose.yml`
2. **Use strong SECRET_KEY and JWT_SECRET_KEY**
3. **Set FLASK_ENV=production and FLASK_DEBUG=0**
4. **Use external MySQL database** (update DATABASE_URL)
5. **Set up reverse proxy** (nginx/traefik) for SSL/TLS
6. **Configure proper backup strategy** for volumes
7. **Use Docker secrets** for sensitive data

## Troubleshooting

### Database connection issues
- Wait for database to be healthy (check with `docker-compose ps`)
- Verify DATABASE_URL matches docker-compose.yml settings
- Check database logs: `docker-compose logs db`

### Application not starting
- Check application logs: `docker-compose logs web`
- Verify all environment variables are set correctly
- Ensure database is healthy before web service starts

### FaceAI dependencies not working
- The Dockerfile includes all necessary system dependencies
- If face-recognition fails, check logs for dlib compilation errors
- Rebuild the image: `docker-compose build --no-cache web`

### Port conflicts
- Change port mappings in `docker-compose.yml` if ports are already in use
- Example: Change `"8000:8000"` to `"8001:8000"` to use port 8001

## Health Checks

All services include health checks:
- **Database**: Checks MySQL connectivity
- **Web**: Checks HTTP endpoint `/api/v1/health`

View health status:
```bash
docker-compose ps
```

## Network

All services are connected via the `vigilanteye_network` bridge network, allowing them to communicate using service names (e.g., `db` for the database).

