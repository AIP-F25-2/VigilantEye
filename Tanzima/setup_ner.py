"""
Setup script for the Comprehensive NER System
This script helps install dependencies and download required models
"""

import subprocess
import sys
import os
import requests
import zipfile
from pathlib import Path

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package}")
        return False

def download_yolo_models():
    """Download YOLO models if they don't exist"""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # YOLO model files
    yolo_files = {
        "yolov3-tiny.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg",
        "yolov3-tiny.weights": "https://pjreddie.com/media/files/yolov3-tiny.weights",
        "coco.names": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
    }
    
    for filename, url in yolo_files.items():
        filepath = models_dir / filename
        
        if filepath.exists():
            print(f"✓ {filename} already exists")
            continue
            
        print(f"Downloading {filename}...")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ Downloaded {filename}")
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}")

def setup_spacy():
    """Setup spaCy model"""
    try:
        import spacy
        # Try to load the model
        spacy.load("en_core_web_sm")
        print("✓ spaCy model already installed")
        return True
    except OSError:
        print("Installing spaCy English model...")
        try:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            print("✓ spaCy model installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install spaCy model")
            return False

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    try:
        import pytesseract
        # Try to get tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR found (version: {version})")
        return True
    except Exception as e:
        print(f"✗ Tesseract OCR not found: {e}")
        print("\nTo install Tesseract OCR:")
        print("  macOS: brew install tesseract")
        print("  Ubuntu: sudo apt-get install tesseract-ocr")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        return False

def main():
    """Main setup function"""
    print("Comprehensive NER System Setup")
    print("=" * 40)
    
    # Install Python packages
    print("\n1. Installing Python packages...")
    packages = [
        "opencv-python>=4.5.0",
        "numpy>=1.21.0", 
        "spacy>=3.4.0",
        "pytesseract>=0.3.10",
        "Pillow>=8.3.0",
        "requests>=2.25.0"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\nInstalled {success_count}/{len(packages)} packages")
    
    # Setup spaCy
    print("\n2. Setting up spaCy...")
    setup_spacy()
    
    # Check Tesseract
    print("\n3. Checking Tesseract OCR...")
    check_tesseract()
    
    # Download YOLO models
    print("\n4. Downloading YOLO models...")
    download_yolo_models()
    
    # Create necessary directories
    print("\n5. Creating directories...")
    directories = ["uploads", "outputs", "models"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    print("\n" + "=" * 40)
    print("Setup completed!")
    print("\nTo test the system, run:")
    print("python ner_demo.py")
    print("\nTo analyze your own image, run:")
    print("python ner_demo.py path/to/your/image.jpg")

if __name__ == "__main__":
    main()


