from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
from utils import predict_audio_class

app = Flask(__name__)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/")
def index():
    """
    Render the upload page.
    """
    return render_template("index.html")

@app.route("/predict", methods=["POST"])

def predict():
    """
    Handle file uploads and return predictions.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(UPLOAD_DIR, secure_filename(file.filename))
    file.save(filepath)

    try:
        # Run prediction
        label = predict_audio_class(filepath)

        # Check if the request came from browser form (not API)
        if request.accept_mimetypes.accept_html:
            return render_template("index.html", filename=file.filename, prediction=label)

        # For API calls (like curl)
        return jsonify({"prediction": label}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
