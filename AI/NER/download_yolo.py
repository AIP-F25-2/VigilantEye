#!/usr/bin/env python3
"""
Script to download YOLO model files
"""
import urllib.request
import os

# Create models directory if it doesn't exist
os.makedirs("models", exist_ok=True)

# URLs for YOLO files
yolo_files = {
    "models/yolov3-tiny.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg",
    "models/yolov3-tiny.weights": "https://pjreddie.com/media/files/yolov3-tiny.weights",
    "models/coco.names": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
}

print("Downloading YOLO model files...")
for filename, url in yolo_files.items():
    print(f"Downloading {filename}...")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"✓ Downloaded {filename}")
    except Exception as e:
        print(f"✗ Failed to download {filename}: {e}")

print("\nDone! You can now run ner_module.py")

