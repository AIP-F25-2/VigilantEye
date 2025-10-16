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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
