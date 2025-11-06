import os
import cv2
import numpy as np
import torch
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
from demographics import DemographicsAnalyzer
from FaceDetection import ImprovedFaceDetector
from Ambiguity import SimpleAmbiguityChecker
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# Initialize Flask app
app = Flask(__name__)


# === Configuration and Initialization ===


# Local model directory and device setup for the LLM
LOCAL_DIR = Path(__file__).parent / "models" / "tinyllama"
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
local_dir_path = Path(__file__).parent / "models" / "tinyllama"
model_path_str = str(local_dir_path.resolve())


dtype = torch.float16 if torch.cuda.is_available() else torch.float32
device = "cuda" if torch.cuda.is_available() else "cpu"


# Load tokenizer and model (LLM)
tokenizer = AutoTokenizer.from_pretrained(model_path_str, use_fast=True, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path_str,
    torch_dtype=dtype,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    local_files_only=True
).to(device)



# Upload folder for image-based APIs
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Initialize demographics analyzer
analyzer = DemographicsAnalyzer()


# Initialize face detector
detector = ImprovedFaceDetector(similarity_threshold=0.35)


# Initialize ambiguity checker
checker = SimpleAmbiguityChecker()


# === Accuracy Metrics Tracking ===

class MetricsTracker:
    def __init__(self):
        self.face_detection_metrics = {
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "total_detections": 0
        }
        
        self.age_gender_metrics = {
            "total_predictions": 0,
            "correct_age_predictions": 0,
            "correct_gender_predictions": 0,
            "age_errors": []  # Store absolute errors for MAE calculation
        }
        
        self.ambiguity_metrics = {
            "total_checks": 0,
            "correct_classifications": 0,
            "false_positives": 0,  # Predicted ambiguous but not
            "false_negatives": 0   # Predicted not ambiguous but was
        }
        
        self.last_reset = datetime.now()
    
    def reset(self):
        """Reset all metrics"""
        self.__init__()
    
    def get_face_detection_accuracy(self):
        """Calculate precision, recall, and F1 score for face detection"""
        tp = self.face_detection_metrics["true_positives"]
        fp = self.face_detection_metrics["false_positives"]
        fn = self.face_detection_metrics["false_negatives"]
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "total_detections": self.face_detection_metrics["total_detections"]
        }
    
    def get_age_gender_accuracy(self):
        """Calculate accuracy for age and gender predictions"""
        total = self.age_gender_metrics["total_predictions"]
        
        if total == 0:
            return {
                "gender_accuracy": 0,
                "age_mae": 0,
                "total_predictions": 0
            }
        
        gender_accuracy = self.age_gender_metrics["correct_gender_predictions"] / total
        age_mae = sum(self.age_gender_metrics["age_errors"]) / len(self.age_gender_metrics["age_errors"]) if self.age_gender_metrics["age_errors"] else 0
        
        return {
            "gender_accuracy": round(gender_accuracy, 4),
            "age_mae": round(age_mae, 2),  # Mean Absolute Error
            "total_predictions": total
        }
    
    def get_ambiguity_accuracy(self):
        """Calculate accuracy for ambiguity checker"""
        total = self.ambiguity_metrics["total_checks"]
        
        if total == 0:
            return {
                "accuracy": 0,
                "precision": 0,
                "recall": 0,
                "total_checks": 0
            }
        
        correct = self.ambiguity_metrics["correct_classifications"]
        fp = self.ambiguity_metrics["false_positives"]
        fn = self.ambiguity_metrics["false_negatives"]
        tp = correct - (total - fp - fn - correct)  # True positives
        
        accuracy = correct / total
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "total_checks": total,
            "correct_classifications": correct
        }


# Initialize metrics tracker
metrics_tracker = MetricsTracker()


# === Routes ===


# Health Check for LLM API
@app.route("/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": LOCAL_DIR}), 200


# LLM Chat API
SYSTEM_PROMPT = "You are a helpful assistant."
def build_chat(messages):
    sys = next((m["content"] for m in messages if m.get("role") == "system"), SYSTEM_PROMPT)
    convo = [f"<|system|>\n{sys}"]
    for m in messages:
        if m["role"] == "user":
            convo.append(f"<|user|>\n{m['content']}")
        elif m["role"] == "assistant":
            convo.append(f"<|assistant|>\n{m['content']}")
    convo.append("<|assistant|>\n")
    return "\n".join(convo)


@app.route("/v1/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    messages = data.get("messages") or [{"role": "user", "content": data.get("prompt", "")}]
    max_new_tokens = int(data.get("max_new_tokens", 256))
    temperature = float(data.get("temperature", 0.7))
    top_p = float(data.get("top_p", 0.9))


    prompt = build_chat(messages)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature,
            top_p=top_p,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(ids[0], skip_special_tokens=True)
    reply = text.split("<|assistant|>")[-1].strip()
    return jsonify({"reply": reply})


# Age/Gender Detection Upload Page
@app.route("/agegender", methods=["GET"])
def agegender_index():
    return '''
<h2>Upload an image for Age/Gender Detection</h2>
<form method="post" enctype="multipart/form-data" action="/agegender/analyze">
    <input type="file" name="image">
    <input type="submit" value="Analyze">
</form>
'''


@app.route("/agegender/analyze", methods=["POST"])
def agegender_analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400


    file = request.files["image"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)


    results, processed_frame = analyzer.analyze(filepath)


    output_path = os.path.join(UPLOAD_FOLDER, "result_" + file.filename)
    cv2.imwrite(output_path, processed_frame)


    return jsonify({
        "detections": results,
        "processed_image": output_path
    })


@app.route("/agegender/analyze_with_groundtruth", methods=["POST"])
def agegender_analyze_with_groundtruth():
    """
    Analyze age/gender with ground truth for accuracy calculation
    Expected JSON payload:
    {
        "ground_truth": [
            {"age": 25, "gender": "Male"},
            {"age": 30, "gender": "Female"}
        ]
    }
    """
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400


    file = request.files["image"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)


    results, processed_frame = analyzer.analyze(filepath)
    
    # Get ground truth from request
    ground_truth_data = request.form.get("ground_truth")
    if ground_truth_data:
        import json
        ground_truth = json.loads(ground_truth_data)
        
        # Compare predictions with ground truth
        for i, detection in enumerate(results):
            if i < len(ground_truth):
                gt = ground_truth[i]
                predicted_age = detection.get("age", 0)
                predicted_gender = detection.get("gender", "")
                
                # Update metrics
                metrics_tracker.age_gender_metrics["total_predictions"] += 1
                
                # Check gender accuracy
                if predicted_gender.lower() == gt["gender"].lower():
                    metrics_tracker.age_gender_metrics["correct_gender_predictions"] += 1
                
                # Calculate age error
                age_error = abs(predicted_age - gt["age"])
                metrics_tracker.age_gender_metrics["age_errors"].append(age_error)


    output_path = os.path.join(UPLOAD_FOLDER, "result_" + file.filename)
    cv2.imwrite(output_path, processed_frame)


    return jsonify({
        "detections": results,
        "processed_image": output_path,
        "current_metrics": metrics_tracker.get_age_gender_accuracy()
    })


# Face Detection API
@app.route("/faces", methods=["GET"])
def faces_home():
    return "✅ Improved Face Detector API is running!"


@app.route("/faces/detect", methods=["POST"])
def detect_faces():
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400


        file = request.files["image"]
        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)


        results, _ = detector.process_image(img, show_result=False)
        
        metrics_tracker.face_detection_metrics["total_detections"] += len(results)


        response = []
        for r in results:
            response.append({
                "person_id": r["person_id"],
                "is_new_person": r["is_new_person"],
                "similarity_score": float(r["similarity_score"]),
                "bounding_box": [int(v) for v in r["bounding_box"]]
            })


        return jsonify({
            "faces_detected": len(results),
            "results": response
        })


    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/faces/detect_with_groundtruth", methods=["POST"])
def detect_faces_with_groundtruth():
    """
    Detect faces with ground truth for accuracy calculation
    Expected form data:
    - image: image file
    - num_faces: number of actual faces in the image (ground truth)
    """
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400


        file = request.files["image"]
        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)


        results, _ = detector.process_image(img, show_result=False)
        
        # Get ground truth
        num_faces_gt = int(request.form.get("num_faces", 0))
        detected_faces = len(results)
        
        # Update metrics
        if detected_faces == num_faces_gt:
            metrics_tracker.face_detection_metrics["true_positives"] += detected_faces
        elif detected_faces > num_faces_gt:
            metrics_tracker.face_detection_metrics["true_positives"] += num_faces_gt
            metrics_tracker.face_detection_metrics["false_positives"] += (detected_faces - num_faces_gt)
        else:  # detected_faces < num_faces_gt
            metrics_tracker.face_detection_metrics["true_positives"] += detected_faces
            metrics_tracker.face_detection_metrics["false_negatives"] += (num_faces_gt - detected_faces)
        
        metrics_tracker.face_detection_metrics["total_detections"] += detected_faces


        response = []
        for r in results:
            response.append({
                "person_id": r["person_id"],
                "is_new_person": r["is_new_person"],
                "similarity_score": float(r["similarity_score"]),
                "bounding_box": [int(v) for v in r["bounding_box"]]
            })


        return jsonify({
            "faces_detected": detected_faces,
            "ground_truth_faces": num_faces_gt,
            "results": response,
            "current_metrics": metrics_tracker.get_face_detection_accuracy()
        })


    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Ambiguity Checker API
@app.route("/ambiguity", methods=["GET"])
def ambiguity_home():
    return "✅ Ambiguity Checker API is running!"


@app.route("/ambiguity/check", methods=["POST"])
def check_ambiguity():
    try:
        if "image1" not in request.files or "image2" not in request.files:
            return jsonify({"error": "Please upload image1 and image2"}), 400


        file1 = request.files["image1"]
        file2 = request.files["image2"]


        npimg1 = np.frombuffer(file1.read(), np.uint8)
        npimg2 = np.frombuffer(file2.read(), np.uint8)


        img1 = cv2.imdecode(npimg1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(npimg2, cv2.IMREAD_COLOR)


        is_ambiguous, score, details = checker.check_ambiguity(img1, img2, show_result=False)


        result = {
            "ambiguous": bool(is_ambiguous),
            "score": float(score),
            "similarities": {k: float(v) for k, v in details['similarities'].items()},
            "reasons": details['reasons']
        }


        return jsonify(result)


    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ambiguity/check_with_groundtruth", methods=["POST"])
def check_ambiguity_with_groundtruth():
    """
    Check ambiguity with ground truth for accuracy calculation
    Expected form data:
    - image1, image2: image files
    - is_ambiguous: "true" or "false" (ground truth)
    """
    try:
        if "image1" not in request.files or "image2" not in request.files:
            return jsonify({"error": "Please upload image1 and image2"}), 400


        file1 = request.files["image1"]
        file2 = request.files["image2"]


        npimg1 = np.frombuffer(file1.read(), np.uint8)
        npimg2 = np.frombuffer(file2.read(), np.uint8)


        img1 = cv2.imdecode(npimg1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(npimg2, cv2.IMREAD_COLOR)


        is_ambiguous, score, details = checker.check_ambiguity(img1, img2, show_result=False)
        
        # Get ground truth
        is_ambiguous_gt = request.form.get("is_ambiguous", "").lower() == "true"
        
        # Update metrics
        metrics_tracker.ambiguity_metrics["total_checks"] += 1
        
        if is_ambiguous == is_ambiguous_gt:
            metrics_tracker.ambiguity_metrics["correct_classifications"] += 1
        else:
            if is_ambiguous and not is_ambiguous_gt:
                metrics_tracker.ambiguity_metrics["false_positives"] += 1
            else:
                metrics_tracker.ambiguity_metrics["false_negatives"] += 1


        result = {
            "ambiguous": bool(is_ambiguous),
            "ground_truth": is_ambiguous_gt,
            "correct": is_ambiguous == is_ambiguous_gt,
            "score": float(score),
            "similarities": {k: float(v) for k, v in details['similarities'].items()},
            "reasons": details['reasons'],
            "current_metrics": metrics_tracker.get_ambiguity_accuracy()
        }


        return jsonify(result)


    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Metrics Endpoints ===

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Get all accuracy metrics"""
    return jsonify({
        "face_detection": metrics_tracker.get_face_detection_accuracy(),
        "age_gender": metrics_tracker.get_age_gender_accuracy(),
        "ambiguity": metrics_tracker.get_ambiguity_accuracy(),
        "last_reset": metrics_tracker.last_reset.isoformat()
    })


@app.route("/metrics/reset", methods=["POST"])
def reset_metrics():
    """Reset all metrics"""
    metrics_tracker.reset()
    return jsonify({
        "status": "success",
        "message": "All metrics have been reset",
        "reset_time": metrics_tracker.last_reset.isoformat()
    })


@app.route("/metrics/face_detection", methods=["GET"])
def get_face_detection_metrics():
    """Get face detection accuracy metrics"""
    return jsonify(metrics_tracker.get_face_detection_accuracy())


@app.route("/metrics/age_gender", methods=["GET"])
def get_age_gender_metrics():
    """Get age/gender prediction accuracy metrics"""
    return jsonify(metrics_tracker.get_age_gender_accuracy())


@app.route("/metrics/ambiguity", methods=["GET"])
def get_ambiguity_metrics():
    """Get ambiguity checker accuracy metrics"""
    return jsonify(metrics_tracker.get_ambiguity_accuracy())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


# Step 1: Clone the Git repository (run this in your terminal, not Python)
# git clone <repo-url>

# Step 2: Navigate to the project directory (in terminal)
# cd "E:\AIP 2025\Git-AIP 2025\VigilantEye-1"

# Step 3: Create a virtual environment (in terminal)
# python -m venv venv

# Step 4: Activate the virtual environment
# In PowerShell:
# .\venv\Scripts\Activate.ps1
# In Command Prompt:
# .\venv\Scripts\activate.bat

# Step 5: Install required dependencies
# If requirements.txt exists:
# pip install -r requirements.txt
# Otherwise, install manually:
# pip install face_recognition matplotlib scikit-learn flask transformers torch numpy opencv-python

# Step 6: Run the Python script
# python merged_Sri.py

# Additional notes:
# - Always activate the virtual environment before running/installing packages
# - If you get missing module errors, install them using pip install <module>
