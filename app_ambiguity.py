from flask import Flask, request, jsonify
import cv2
import numpy as np
from Ambiguity import SimpleAmbiguityChecker

# Initialize Flask app
app = Flask(__name__)

# Load the ambiguity checker model
checker = SimpleAmbiguityChecker()

@app.route("/")
def home():
    return "✅ Ambiguity Checker API is running!"

@app.route("/check", methods=["POST"])
def check():
    try:
        # Expecting 2 image files: "image1" and "image2"
        if "image1" not in request.files or "image2" not in request.files:
            return jsonify({"error": "Please upload image1 and image2"}), 400

        file1 = request.files["image1"]
        file2 = request.files["image2"]

        # Read images as OpenCV arrays
        npimg1 = np.frombuffer(file1.read(), np.uint8)
        npimg2 = np.frombuffer(file2.read(), np.uint8)

        img1 = cv2.imdecode(npimg1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(npimg2, cv2.IMREAD_COLOR)

        # Run ambiguity check (disable visualization for API)
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
    app.run(debug=True)
