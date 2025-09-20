#!/bin/bash
set -e

echo "Starting VigilantEye API..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Database is ready!"

# Initialize database tables
echo "Initializing database tables..."
python init_db.py

# Start the application
echo "Starting FastAPI application..."
exec python run.py
