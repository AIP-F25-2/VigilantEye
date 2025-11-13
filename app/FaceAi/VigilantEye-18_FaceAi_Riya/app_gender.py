from flask import Flask, request, jsonify, render_template
import os, cv2
from werkzeug.utils import secure_filename
from demographics import DemographicsAnalyzer

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load model once
analyzer = DemographicsAnalyzer()

@app.route("/", methods=["GET"])
def index():
    return '''
    <h2>Upload an image for Age/Gender Detection</h2>
    <form method="post" enctype="multipart/form-data" action="/analyze">
        <input type="file" name="image">
        <input type="submit" value="Analyze">
    </form>
    '''

@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    # Sanitize filename to prevent path traversal
    safe_filename = secure_filename(file.filename)
    if not safe_filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
    file.save(filepath)

    results, processed_frame = analyzer.analyze(filepath)

    # save processed image with labels
    output_path = os.path.join(UPLOAD_FOLDER, "result_" + safe_filename)
    cv2.imwrite(output_path, processed_frame)

    return jsonify({
        "detections": results,
        "processed_image": output_path
    })

if __name__ == "__main__":
    app.run(debug=True,port=5000)
