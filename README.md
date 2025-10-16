# VigilantEye-1

A Flask-based AI API for face detection, demographics/ambiguity analysis, and conversational LLM responses.  
**Note:** The `models`, `uploads`, and `venv` folders are NOT pushed to the repository. Models and the virtual environment must be built locally.

---

## Features

- LLM-powered chat endpoint using TinyLlama
- Face detection and cross-image recognition API (OpenCV, custom models)
- Age/Gender prediction from images
- Ambiguity checker: compare two images for similarity/confusion
- REST API endpoints for integration

---

## Setup Instructions

1. **Clone this repo and create a Python virtual environment**
   ```
   git clone <repo-url>
   cd VigilantEye-1
   python -m venv venv
   # For Windows:
   venv\Scripts\activate
   # For Mac/Linux:
   source venv/bin/activate
   ```

2. **Install required packages**
   ```
   pip install -r requirements.txt
   ```

3. **Download models using the provided script**
   - The `models` folder is ignored in version control. You need to download required models before running the app.
   ```
   python download_and_save.py
   # This script will fetch TinyLlama, OpenCV, and age/gender detector models into ./models/
   ```

   If required, download additional detector/model files and place them in:
   ```
   VigilantEye-1/
     models/
       tinyllama/                   # Contains TinyLlama weights
       opencv_face_detector_uint8.pb
       opencv_face_detector.pbtxt
       age_net.caffemodel
       age_deploy.prototxt
       gender_net.caffemodel
       gender_deploy.prototxt
   ```

4. **(Optional) Create the uploads directory**
   - This app saves temporary files in an `uploads` folder.
   ```
   mkdir uploads
   ```

5. **Run the application**
   ```
   python merged_Sri.py
   ```

---

## API Endpoints

| Endpoint                           | Method | Type        | Description                              |
|-------------------------------------|--------|-------------|------------------------------------------|
| `/v1/health`                       | GET    | Status      | Returns API health and model info        |
| `/v1/chat`                         | POST   | JSON        | Chat with conversational LLM             |
| `/faces`                           | GET    | Status      | Returns Face API status                  |
| `/faces/detect`                    | POST   | form-data   | Upload image for face detection          |
| `/agegender`                       | GET    | UI          | Web form to upload image for analysis    |
| `/agegender/analyze`               | POST   | form-data   | Upload image to predict age/gender       |
| `/ambiguity`                       | GET    | Status      | Returns ambiguity API status             |
| `/ambiguity/check`                 | POST   | form-data   | Compare two images for similarity        |

---

## Example Usage

**Chat**
```
curl -X POST http://localhost:5000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello, AI!"}]}'
```

**Face Detection**
```
curl -X POST -F "image=@example.jpg" http://localhost:5000/faces/detect
```

**Age/Gender Detection**
```
curl -X POST -F "image=@person.jpg" http://localhost:5000/agegender/analyze
```

**Ambiguity Checker**
```
curl -X POST \
  -F "image1=@face1.jpg" \
  -F "image2=@face2.jpg" \
  http://localhost:5000/ambiguity/check
```

---

## Notes

- All model files are **not included in the repo** and must be downloaded/built using `download_and_save.py` or manually.
- The `uploads` and `venv` directories are user/system-specific and should be built locally.
- Ensure all model files are present before launching the server.
- Use Postman or curl for POST endpoints (especially for file upload).
- LLM requires compatible PyTorch version and sufficient RAM.

---