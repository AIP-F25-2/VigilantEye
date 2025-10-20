#!/bin/bash

# VigilantEYE Backend Startup Script (Linux/Mac)

echo "=================================="
echo "🚀 VigilantEYE Backend Startup"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements/development.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
    exit 1
fi

# Check database connection
echo "Checking database connection..."
python -c "from src.config import get_settings; s = get_settings(); print(f'Database: {s.db_host}:{s.db_port}/{s.db_name}')"

# Start the server
echo ""
echo "Starting server..."
python run.py
