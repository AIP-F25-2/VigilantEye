# AI Models Cache Directory

This directory stores downloaded AI model files used by the VigilentEye platform. Models are fetched automatically on first use and cached locally so they can be reused across restarts and deployments.

## Supported Models
1. **Phi-3-Mini** (`microsoft/Phi-3-mini-4k-instruct`)
   - Format: `.pt`
   - Approximate size: 7.5 GB
   - Location: `models/phi3/`

2. **YOLOv8x** (`ultralytics`)
   - Format: `.pt`
   - Approximate size: 136 MB
   - Location: `models/yolov8/yolov8x.pt`

3. **Whisper Base** (`openai/whisper`)
   - Format: `.pt`
   - Approximate size: 139 MB
   - Location: `models/whisper/base.pt`

4. **BLIP-2** (`Salesforce/blip-image-captioning-large`)
   - Format: `.pt`
   - Approximate size: 1.9 GB
   - Location: `models/blip2/`

5. **RetinaFace**
   - Format: `.pth`
   - Approximate size: 27 MB
   - Location: `models/retinaface/`

6. **YAMNet** (`tensorflow-hub`)
   - Format: TensorFlow SavedModel
   - Approximate size: 13 MB
   - Location: `models/yamnet/`

## Usage Notes
- The application downloads models automatically when they are first requested.
- You may pre-download models and place them in the appropriate subdirectories to speed up the initial startup.
- The `models/` directory is mounted as a Docker volume to persist files across container restarts.
- Ensure at least 15 GB of free disk space to accommodate all models.

All models listed are open-source and free to use.

