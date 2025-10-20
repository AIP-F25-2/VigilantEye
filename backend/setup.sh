#!/bin/bash
# Setup script for VigilantEYE Backend (Linux/Mac)

echo "===================================="
echo "🔧 VigilantEYE Backend Setup"
echo "===================================="

# Remove old virtual environment
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements/development.txt

# Verify installation
echo ""
echo "Verifying installation..."
python -c "from jose import jwt; print('✅ JWT library installed correctly!')"
python -c "import fastapi; print('✅ FastAPI installed correctly!')"
python -c "import sqlalchemy; print('✅ SQLAlchemy installed correctly!')"

echo ""
echo "===================================="
echo "✅ Setup Complete!"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Edit .env with your MySQL credentials"
echo "3. Create database: CREATE DATABASE vigilanteye_db;"
echo "4. Run migrations: python scripts/migrate.py create"
echo "5. Start server: python run.py"
echo ""
