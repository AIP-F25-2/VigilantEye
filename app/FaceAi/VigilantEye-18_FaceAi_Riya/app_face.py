from flask import Flask, request, jsonify
import cv2
import numpy as np
from FaceDetection import ImprovedFaceDetector

# Initialize Flask app
app = Flask(__name__)

# Initialize the improved detector
detector = ImprovedFaceDetector(similarity_threshold=0.35)

@app.route("/")
def home():
    return "✅ Improved Face Detector API is running!"

@app.route("/detect", methods=["POST"])
def detect_faces():
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400

        file = request.files["image"]

        # Read image into OpenCV format
        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # Process image (disable visualization for API)
        results, _ = detector.process_image(img, show_result=False)

        # Format response
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


if __name__ == "__main__":
    app.run(debug=True,port=5001)
