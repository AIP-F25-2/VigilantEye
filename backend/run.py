"""
Enhanced run.py with better error handling and Python path detection.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding for emoji characters
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for Windows console
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Fallback: just continue without emoji if encoding fails
        pass

def safe_print(text: str, fallback: str = None):
    """Print text, falling back to ASCII if Unicode fails."""
    try:
        print(text)
    except UnicodeEncodeError:
        if fallback:
            print(fallback)
        else:
            # Remove emoji and special characters
            safe_text = text.encode('ascii', 'ignore').decode('ascii')
            print(safe_text)

def check_python_environment():
    """Check if we're using the correct Python environment."""
    python_exe = sys.executable
    venv_path = Path(__file__).parent / "venv" / "Scripts" / "python.exe"
    
    print("=" * 60)
    print("Python Environment Check")
    print("=" * 60)
    print(f"Python Executable: {python_exe}")
    print(f"Python Version: {sys.version}")
    print(f"Expected Venv: {venv_path}")
    
    # Check if we're in the venv
    if "venv" in python_exe or "Scripts" in python_exe:
        safe_print("✅ Using virtual environment Python", "[OK] Using virtual environment Python")
    else:
        safe_print("⚠️  WARNING: May not be using virtual environment!", "[WARNING] May not be using virtual environment!")
        print(f"   Expected venv Python: {venv_path}")
        if venv_path.exists():
            safe_print(f"   💡 Try running: {venv_path} run.py", f"   Try running: {venv_path} run.py")
    
    print()

def check_required_libraries():
    """Check if required libraries are installed."""
    required_libs = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "pymysql",
    ]
    
    # Critical optional libraries that should be checked
    optional_critical_libs = [
        "email_validator",  # Required for pydantic email validation
        "facenet_pytorch",  # Required for face recognition
        "easyocr",  # Required for OCR/text detection
        "ultralytics",  # Required for YOLO object detection
        "openai",  # Required for LLM/threat detection
        "transformers",  # Required for HuggingFace models
        "librosa",  # Required for audio processing
    ]
    
    print("=" * 60)
    print("Library Check")
    print("=" * 60)
    
    missing = []
    warnings = []
    
    # Check required libraries
    for lib in required_libs:
        try:
            module = __import__(lib)
            version = getattr(module, "__version__", "unknown")
            safe_print(f"✅ {lib:20s} - {version}", f"[OK] {lib:20s} - {version}")
        except ImportError:
            safe_print(f"❌ {lib:20s} - NOT FOUND", f"[FAIL] {lib:20s} - NOT FOUND")
            missing.append(lib)
    
    # Check optional but critical libraries
    for lib in optional_critical_libs:
        try:
            module = __import__(lib)
            version = getattr(module, "__version__", "unknown")
            safe_print(f"✅ {lib:20s} - {version}", f"[OK] {lib:20s} - {version}")
        except ImportError:
            safe_print(f"⚠️  {lib:20s} - NOT FOUND (may cause runtime errors)", f"[WARN] {lib:20s} - NOT FOUND (may cause runtime errors)")
            warnings.append(lib)
    
    print()
    
    if missing:
        print("=" * 60)
        print("ERROR: Missing Required Libraries")
        print("=" * 60)
        print(f"Missing: {', '.join(missing)}")
        print()
        print("To install missing libraries:")
        print("  venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        print()
        return False
    
    if warnings:
        print("=" * 60)
        safe_print("⚠️  WARNING: Missing Optional Critical Libraries", "[WARNING] Missing Optional Critical Libraries")
        print("=" * 60)
        print(f"Missing: {', '.join(warnings)}")
        print()
        print("These libraries are in requirements.txt but not installed.")
        print("Some features may not work properly.")
        print("To install:")
        print("  venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        print()
    
    return True

def add_backend_to_path():
    """Add backend directory to Python path."""
    backend_dir = Path(__file__).parent
    backend_str = str(backend_dir)
    
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)
        print(f"Added to Python path: {backend_dir}")

if __name__ == "__main__":
    try:
        # Check environment
        check_python_environment()
        
        # Check libraries
        if not check_required_libraries():
            sys.exit(1)
        
        # Add backend to path
        add_backend_to_path()
        
        # Import after path setup
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
        print()
        
        uvicorn.run(
            "src.main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=settings.is_development,
            log_level=settings.log_level.lower(),
            reload_includes=["*.py", "*.yaml", "*.yml"],
            reload_excludes=["*.log", "__pycache__", "*.pyc"],
        )
        
    except ImportError as e:
        print("=" * 60)
        safe_print("❌ Import Error", "[ERROR] Import Error")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("This usually means:")
        print("1. Virtual environment not activated")
        print("2. Libraries not installed in venv")
        print("3. Using wrong Python interpreter")
        print()
        print("Solutions:")
        print("1. Run: venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        print("2. Use: venv\\Scripts\\python.exe run.py")
        print("3. Or use: start.bat")
        sys.exit(1)
    except Exception as e:
        print("=" * 60)
        safe_print("❌ Error Starting Server", "[ERROR] Error Starting Server")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
