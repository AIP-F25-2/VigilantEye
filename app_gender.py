from flask import Flask, request, jsonify, render_template
import os, cv2
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
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    results, processed_frame = analyzer.analyze(filepath)

    # save processed image with labels
    output_path = os.path.join(UPLOAD_FOLDER, "result_" + file.filename)
    cv2.imwrite(output_path, processed_frame)

    return jsonify({
        "detections": results,
        "processed_image": output_path
    })

if __name__ == "__main__":
    app.run(debug=True,port=5000)
