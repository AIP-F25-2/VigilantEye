"""
Integrated Face Detection API for VigilantEye
Combines face recognition, demographics analysis, and real-time detection
"""

from flask import Flask, request, jsonify, render_template_string
import cv2
import numpy as np
import os
import json
from datetime import datetime
from FaceDetection import ImprovedFaceDetector
from demographics import DemographicsAnalyzer

class VigilantEyeFaceAI:
    """Integrated Face AI system for VigilantEye"""
    
    def __init__(self, models_dir="face_ai/models"):
        self.models_dir = models_dir
        self.face_detector = ImprovedFaceDetector(similarity_threshold=0.35)
        self.demographics_analyzer = DemographicsAnalyzer(models_dir)
        self.detection_history = []
        
        print("✅ VigilantEye Face AI initialized")
        print(f"   Models directory: {models_dir}")
        print(f"   Face detector threshold: 0.35")
    
    def process_image_comprehensive(self, image_path_or_array, include_demographics=True):
        """
        Comprehensive image processing with face detection and demographics
        """
        try:
            # Load image
            if isinstance(image_path_or_array, str):
                if not os.path.exists(image_path_or_array):
                    return {"error": "Image file not found"}, None
                image = cv2.imread(image_path_or_array)
                if image is None:
                    return {"error": "Could not load image"}, None
            else:
                image = image_path_or_array.copy()
            
            # Face detection and recognition
            face_results, annotated_image = self.face_detector.process_image(
                image, show_result=False
            )
            
            # Demographics analysis for each detected face
            if include_demographics and face_results:
                demographics_results = self.analyze_demographics(image, face_results)
                
                # Combine face recognition with demographics
                for i, face_result in enumerate(face_results):
                    if i < len(demographics_results):
                        face_result.update(demographics_results[i])
            
            # Store detection in history
            detection_record = {
                "timestamp": datetime.now().isoformat(),
                "faces_detected": len(face_results),
                "results": face_results
            }
            self.detection_history.append(detection_record)
            
            # Keep only last 100 detections
            if len(self.detection_history) > 100:
                self.detection_history = self.detection_history[-100:]
            
            return {
                "success": True,
                "faces_detected": len(face_results),
                "results": face_results,
                "timestamp": detection_record["timestamp"]
            }, annotated_image
            
        except Exception as e:
            return {"error": str(e)}, None
    
    def analyze_demographics(self, image, face_results):
        """Analyze demographics for detected faces"""
        try:
            demographics_results = []
            
            for face_result in face_results:
                # Extract face region from bounding box
                top, right, bottom, left = face_result["bounding_box"]
                
                # Add some padding
                padding = 20
                h, w = image.shape[:2]
                x1 = max(0, left - padding)
                y1 = max(0, top - padding)
                x2 = min(w, right + padding)
                y2 = min(h, bottom + padding)
                
                face_crop = image[y1:y2, x1:x2]
                
                # Save temporary face image for demographics analysis
                temp_path = f"temp_face_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                cv2.imwrite(temp_path, face_crop)
                
                try:
                    # Analyze demographics
                    demo_results = self.demographics_analyzer.analyze(temp_path)
                    if demo_results:
                        demographics_results.append(demo_results[0])
                    else:
                        demographics_results.append({
                            "gender": "Unknown",
                            "age_group": "Unknown",
                            "gender_score": 0.0,
                            "age_score": 0.0
                        })
                except Exception as e:
                    print(f"Demographics analysis error: {e}")
                    demographics_results.append({
                        "gender": "Unknown",
                        "age_group": "Unknown",
                        "gender_score": 0.0,
                        "age_score": 0.0
                    })
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            return demographics_results
            
        except Exception as e:
            print(f"Demographics analysis error: {e}")
            return []
    
    def get_detection_stats(self):
        """Get detection statistics"""
        total_detections = len(self.detection_history)
        total_faces = sum(record["faces_detected"] for record in self.detection_history)
        
        return {
            "total_detections": total_detections,
            "total_faces_detected": total_faces,
            "known_persons": len(self.face_detector.known_faces),
            "average_faces_per_detection": total_faces / total_detections if total_detections > 0 else 0
        }
    
    def reset_memory(self):
        """Reset face recognition memory"""
        self.face_detector.reset_memory()
        self.detection_history = []
        print("Face AI memory reset")

# Initialize the Face AI system
face_ai = VigilantEyeFaceAI()

# Flask API endpoints
def create_face_ai_routes(app):
    """Add Face AI routes to the main Flask app"""
    
    @app.route('/face-ai/detect', methods=['POST'])
    def detect_faces():
        """Detect faces with demographics analysis"""
        try:
            if "image" not in request.files:
                return jsonify({"error": "Please upload an image file"}), 400
            
            file = request.files["image"]
            
            # Read image into OpenCV format
            npimg = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            
            # Process image
            result, annotated_image = face_ai.process_image_comprehensive(
                img, include_demographics=True
            )
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/face-ai/detect-simple', methods=['POST'])
    def detect_faces_simple():
        """Simple face detection without demographics"""
        try:
            if "image" not in request.files:
                return jsonify({"error": "Please upload an image file"}), 400
            
            file = request.files["image"]
            
            # Read image into OpenCV format
            npimg = np.frombuffer(file.read(), np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            
            # Process image
            result, annotated_image = face_ai.process_image_comprehensive(
                img, include_demographics=False
            )
            
            if "error" in result:
                return jsonify(result), 500
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/face-ai/stats')
    def get_stats():
        """Get detection statistics"""
        return jsonify(face_ai.get_detection_stats())
    
    @app.route('/face-ai/reset', methods=['POST'])
    def reset_face_memory():
        """Reset face recognition memory"""
        face_ai.reset_memory()
        return jsonify({"message": "Face AI memory reset successfully"})
    
    @app.route('/face-ai/dashboard')
    def face_ai_dashboard():
        """Face AI dashboard page"""
        dashboard_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>VigilantEye - Face AI Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
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
                    <h1>🔍 VigilantEye Face AI Dashboard</h1>
                    <p>Advanced Face Detection, Recognition & Demographics Analysis</p>
                </div>
                
                <div class="upload-area" id="uploadArea">
                    <h3>📸 Upload Image for Face Analysis</h3>
                    <p>Drag and drop an image or click to select</p>
                    <input type="file" id="imageInput" accept="image/*" style="display: none;">
                    <button class="btn" onclick="document.getElementById('imageInput').click()">Choose Image</button>
                </div>
                
                <div style="text-align: center; margin: 20px 0;">
                    <button class="btn" onclick="detectFaces(true)">🔍 Detect with Demographics</button>
                    <button class="btn" onclick="detectFaces(false)">👤 Simple Detection</button>
                    <button class="btn" onclick="loadStats()">📊 View Statistics</button>
                    <button class="btn" onclick="resetMemory()">🔄 Reset Memory</button>
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
                        container.innerHTML = '<div class="face-result"><h3>❌ Error</h3><p>' + data.error + '</p></div>';
                        return;
                    }
                    
                    let html = '<h3>🎯 Detection Results</h3>';
                    html += '<p><strong>Faces Detected:</strong> ' + data.faces_detected + '</p>';
                    html += '<p><strong>Timestamp:</strong> ' + data.timestamp + '</p>';
                    
                    if (data.results && data.results.length > 0) {
                        data.results.forEach((result, index) => {
                            html += '<div class="face-result">';
                            html += '<h4>👤 Person ' + (index + 1) + '</h4>';
                            html += '<p><strong>ID:</strong> ' + result.person_id + '</p>';
                            html += '<p><strong>Status:</strong> ' + (result.is_new_person ? '🆕 New Person' : '✅ Known Person') + '</p>';
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
                                <div class="stat-number">${data.average_faces_per_detection.toFixed(1)}</div>
                                <div class="stat-label">Avg Faces/Detection</div>
                            </div>
                        `;
                    })
                    .catch(error => {
                        console.error('Error loading stats:', error);
                    });
                }
                
                function resetMemory() {
                    if (confirm('Are you sure you want to reset the face recognition memory? This will clear all known faces.')) {
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
    # Test the Face AI system
    print("Testing VigilantEye Face AI...")
    
    # Initialize
    face_ai = VigilantEyeFaceAI()
    
    # Test with sample images if available
    sample_images = [
        "face_ai/uploads/ap1.jpg",
        "face_ai/uploads/ap2.jpg", 
        "face_ai/uploads/ip1.jpg",
        "face_ai/uploads/nm1.jpg"
    ]
    
    for img_path in sample_images:
        if os.path.exists(img_path):
            print(f"\nTesting with: {img_path}")
            result, _ = face_ai.process_image_comprehensive(img_path)
            if "error" not in result:
                print(f"✅ Detected {result['faces_detected']} faces")
                for i, face in enumerate(result['results']):
                    print(f"   Face {i+1}: {face['person_id']} ({'New' if face['is_new_person'] else 'Known'})")
            else:
                print(f"❌ Error: {result['error']}")
    
    print("\n✅ Face AI integration test completed!")
