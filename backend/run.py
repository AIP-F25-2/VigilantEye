"""
Simple run script for VigilantEYE Backend.

This script ensures proper path setup and starts the server.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    import uvicorn
    from src.config import get_settings
    
    settings = get_settings()
    
    print("=" * 60)
    print("🚀 Starting VigilantEYE Backend Server")
    print("=" * 60)
    print(f"Environment: {settings.app_env}")
    print(f"Host: {settings.app_host}")
    print(f"Port: {settings.app_port}")
    print(f"Debug: {settings.app_debug}")
    print(f"API Docs: http://localhost:{settings.app_port}/api/docs")
    print("=" * 60)
    
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
