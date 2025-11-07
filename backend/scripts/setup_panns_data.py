"""
Setup script for PANNs inference data files.
Downloads the required class_labels_indices.csv file for audio classification.
"""

import os
import requests
from pathlib import Path

# URL for the class labels file (from AudioSet)
CLASS_LABELS_URL = "https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv"

def download_panns_data():
    """Download PANNs data files."""
    # Determine the data directory
    # On Windows, it's typically in the user's home directory
    home_dir = Path.home()
    panns_data_dir = home_dir / "panns_data"
    panns_data_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = panns_data_dir / "class_labels_indices.csv"
    
    print("=" * 60)
    print("PANNs Data Setup")
    print("=" * 60)
    print(f"Data directory: {panns_data_dir}")
    print(f"Target file: {csv_file}")
    print()
    
    # Check if file already exists
    if csv_file.exists():
        print(f"✅ File already exists: {csv_file}")
        print("Skipping download.")
        return True
    
    # Download the file
    print(f"Downloading class_labels_indices.csv from {CLASS_LABELS_URL}...")
    try:
        response = requests.get(CLASS_LABELS_URL, timeout=30)
        response.raise_for_status()
        
        # Save the file
        with open(csv_file, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Successfully downloaded to: {csv_file}")
        print(f"File size: {csv_file.stat().st_size} bytes")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading file: {e}")
        print()
        print("You can manually download the file:")
        print(f"1. Go to: {CLASS_LABELS_URL}")
        print(f"2. Save it to: {csv_file}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = download_panns_data()
    if success:
        print()
        print("=" * 60)
        print("✅ PANNs data setup complete!")
        print("=" * 60)
        print("Audio classification should now work after restarting the server.")
    else:
        print()
        print("=" * 60)
        print("⚠️  Setup incomplete")
        print("=" * 60)
        print("Audio classification will be disabled until the data file is available.")
    
    print()

