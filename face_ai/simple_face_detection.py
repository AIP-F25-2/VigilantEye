"""
Simplified Face Detection for VigilantEye
Basic face detection without complex dependencies
"""

from flask import Flask, request, jsonify, render_template_string
import os
import json
from datetime import datetime

class SimpleFaceDetector:
    """Simplified face detector for demo purposes"""
    
    def __init__(self):
        self.detection_history = []
        self.face_counter = 0
        print("Simple Face Detector initialized (demo mode)")
    
    def process_image_simple(self, image_path_or_array):
        """Simple image processing simulation"""
        try:
            # Simulate face detection
            simulated_faces = [
                {
                    "person_id": f"person_{self.face_counter + 1:03d}",
                    "is_new_person": True,
                    "similarity_score": 0.0,
                    "bounding_box": [100, 100, 200, 200],
                    "gender": "Unknown",
                    "age_group": "Unknown",
                    "gender_score": 0.0,
                    "age_score": 0.0
                }
            ]
            
            self.face_counter += 1
            
            # Store detection in history
            detection_record = {
                "timestamp": datetime.now().isoformat(),
                "faces_detected": len(simulated_faces),
                "results": simulated_faces
            }
            self.detection_history.append(detection_record)
            
            # Keep only last 100 detections
            if len(self.detection_history) > 100:
                self.detection_history = self.detection_history[-100:]
            
            return {
                "success": True,
                "faces_detected": len(simulated_faces),
                "results": simulated_faces,
                "timestamp": detection_record["timestamp"],
                "note": "Demo mode - Install OpenCV and face-recognition for real detection"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_detection_stats(self):
        """Get detection statistics"""
        total_detections = len(self.detection_history)
        total_faces = sum(record["faces_detected"] for record in self.detection_history)
        
        return {
            "total_detections": total_detections,
            "total_faces_detected": total_faces,
            "known_persons": self.face_counter,
            "average_faces_per_detection": total_faces / total_detections if total_detections > 0 else 0,
            "mode": "Demo"
        }
    
    def reset_memory(self):
        """Reset face recognition memory"""
        self.detection_history = []
        self.face_counter = 0
        print("Face AI memory reset")

# Initialize the simple Face AI system
simple_face_ai = SimpleFaceDetector()

# Flask API endpoints
def create_simple_face_ai_routes(app):
    """Add simplified Face AI routes to the main Flask app"""
    
    @app.route('/face-ai/detect', methods=['POST'])
    def detect_faces():
        """Detect faces (demo mode)"""
        try:
            if "image" not in request.files:
                return jsonify({"error": "Please upload an image file"}), 400
            
            file = request.files["image"]
            
            # Simulate processing
            result = simple_face_ai.process_image_simple(file)
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/face-ai/detect-simple', methods=['POST'])
    def detect_faces_simple():
        """Simple face detection (demo mode)"""
        try:
            if "image" not in request.files:
                return jsonify({"error": "Please upload an image file"}), 400
            
            file = request.files["image"]
            
            # Simulate processing
            result = simple_face_ai.process_image_simple(file)
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/face-ai/stats')
    def get_stats():
        """Get detection statistics"""
        return jsonify(simple_face_ai.get_detection_stats())
    
    @app.route('/face-ai/reset', methods=['POST'])
    def reset_face_memory():
        """Reset face recognition memory"""
        simple_face_ai.reset_memory()
        return jsonify({"message": "Face AI memory reset successfully"})
    
    @app.route('/face-ai/dashboard')
    def simple_face_ai_dashboard():
        """Face AI dashboard page (demo mode)"""
        dashboard_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VigilantEye - Face AI Dashboard (Demo)</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
                .demo-notice { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .upload-area { border: 2px dashed #3498db; padding: 40px; text-align: center; margin: 20px 0; border-radius: 10px; background: #f8f9fa; }
                .upload-area:hover { background: #e9ecef; }
                .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                .btn:hover { background: #2980b9; }
                .results { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 5px; }
                .face-result { margin: 10px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #3498db; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
                .stat-card { background: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; }
                .stat-number { font-size: 2em; font-weight: bold; color: #2c3e50; }
                .stat-label { color: #7f8c8d; margin-top: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>VigilantEye Face AI Dashboard (Demo Mode)</h1>
                    <p>Basic Face Detection Simulation - Install dependencies for real AI features</p>
                </div>
                
                <div class="demo-notice">
                    <h4>Demo Mode Notice</h4>
                    <p>This is a simplified demo version. To enable real face detection and recognition:</p>
                    <ol>
                        <li>Install CMake from <a href="https://cmake.org/download/" target="_blank">cmake.org</a></li>
                        <li>Run: <code>pip install -r requirements.txt</code></li>
                        <li>Restart the application</li>
                    </ol>
                </div>
                
                <div class="upload-area" id="uploadArea">
                    <h3>Upload Image for Face Analysis (Demo)</h3>
                    <p>Drag and drop an image or click to select</p>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;">
                    <button class="btn" onclick="document.getElementById('imageInput').click()">Choose Image</button>
                </div>
                
                <div style="text-align: center; margin: 20px 0;">
                    <button class="btn" onclick="detectFaces(true)">Detect with Demographics (Demo)</button>
                    <button class="btn" onclick="detectFaces(false)">Simple Detection (Demo)</button>
                    <button class="btn" onclick="loadStats()">View Statistics</button>
                    <button class="btn" onclick="resetMemory()">Reset Memory</button>
                </div>
                
                <div class="stats" id="statsContainer"></div>
                <div class="results" id="resultsContainer" style="display: none;"></div>
            </div>
            
            <script>
                document.getElementById('imageInput').addEventListener('change', function(e) {
                    if (e.target.files.length > 0) {
                        detectFaces(true);
                    }
                });
                
                function detectFaces(includeDemographics) {
                    const fileInput = document.getElementById('imageInput');
                    if (!fileInput.files[0]) {
                        alert('Please select an image first');
                        return;
                    }
                    
                    const formData = new FormData();
                    formData.append('image', fileInput.files[0]);
                    
                    const endpoint = includeDemographics ? '/face-ai/detect' : '/face-ai/detect-simple';
                    
                    fetch(endpoint, {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        displayResults(data);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error processing image: ' + error.message);
                    });
                }
                
                function displayResults(data) {
                    const container = document.getElementById('resultsContainer');
                    container.style.display = 'block';
                    
                    if (data.error) {
                        container.innerHTML = '<div class="face-result"><h3>Error</h3><p>' + data.error + '</p></div>';
                        return;
                    }
                    
                    let html = '<h3>Detection Results (Demo Mode)</h3>';
                    html += '<p><strong>Faces Detected:</strong> ' + data.faces_detected + '</p>';
                    html += '<p><strong>Timestamp:</strong> ' + data.timestamp + '</p>';
                    if (data.note) {
                        html += '<p><strong>Note:</strong> ' + data.note + '</p>';
                    }
                    
                    if (data.results && data.results.length > 0) {
                        data.results.forEach((result, index) => {
                            html += '<div class="face-result">';
                            html += '<h4>Person ' + (index + 1) + '</h4>';
                            html += '<p><strong>ID:</strong> ' + result.person_id + '</p>';
                            html += '<p><strong>Status:</strong> ' + (result.is_new_person ? 'New Person' : 'Known Person') + '</p>';
                            html += '<p><strong>Similarity:</strong> ' + (result.similarity_score * 100).toFixed(1) + '%</p>';
                            
                            if (result.gender) {
                                html += '<p><strong>Gender:</strong> ' + result.gender + ' (' + (result.gender_score * 100).toFixed(1) + '%)</p>';
                            }
                            if (result.age_group) {
                                html += '<p><strong>Age Group:</strong> ' + result.age_group + ' (' + (result.age_score * 100).toFixed(1) + '%)</p>';
                            }
                            
                            html += '</div>';
                        });
                    } else {
                        html += '<p>No faces detected in the image.</p>';
                    }
                    
                    container.innerHTML = html;
                }
                
                function loadStats() {
                    fetch('/face-ai/stats')
                    .then(response => response.json())
                    .then(data => {
                        const container = document.getElementById('statsContainer');
                        container.innerHTML = `
                            <div class="stat-card">
                                <div class="stat-number">${data.total_detections}</div>
                                <div class="stat-label">Total Detections</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.total_faces_detected}</div>
                                <div class="stat-label">Faces Detected</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.known_persons}</div>
                                <div class="stat-label">Known Persons</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.mode}</div>
                                <div class="stat-label">Mode</div>
                            </div>
                        `;
                    })
                    .catch(error => {
                        console.error('Error loading stats:', error);
                    });
                }
                
                function resetMemory() {
                    if (confirm('Are you sure you want to reset the face recognition memory?')) {
                        fetch('/face-ai/reset', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            loadStats();
                        })
                        .catch(error => {
                            console.error('Error resetting memory:', error);
                        });
                    }
                }
                
                // Load stats on page load
                loadStats();
            </script>
        </body>
        </html>
        """
        return dashboard_html

if __name__ == "__main__":
    # Test the simple Face AI system
    print("Testing Simple Face AI...")
    
    # Initialize
    simple_face_ai = SimpleFaceDetector()
    
    # Test
    result = simple_face_ai.process_image_simple("test_image.jpg")
    print(f"Test result: {result}")
    
    print("Simple Face AI test completed!")
