"""
Web interface for the Comprehensive NER System
A Flask-based web application for easy NER analysis
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from werkzeug.utils import secure_filename
from comprehensive_ner_system import ComprehensiveNER
import base64
import cv2
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize NER system
ner = ComprehensiveNER()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_dir():
    """Create upload directory if it doesn't exist"""
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    """Main page"""
    return render_template('ner_index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and NER analysis"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        create_upload_dir()
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Perform NER analysis
            results = ner.detect_all_entities(filepath)
            
            # Create visualization
            output_path = ner.visualize_entities(filepath, f"outputs/{filename}")
            
            # Convert image to base64 for display
            with open(output_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Prepare response
            response = {
                'success': True,
                'filename': filename,
                'image_data': img_base64,
                'entities': results['entities'],
                'extracted_text': results['extracted_text'],
                'text_entities': results['text_entities'],
                'total_entities': len(results['entities']) + len(results['text_entities'])
            }
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    """Analyze text input for NER"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Extract entities from text
        entities = ner.extract_entities_from_text(text)
        
        response = {
            'success': True,
            'text': text,
            'entities': entities,
            'total_entities': len(entities)
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Text analysis failed: {str(e)}'}), 500

@app.route('/demo')
def demo():
    """Demo page with sample images"""
    return render_template('ner_demo.html')

@app.route('/api/entity_types')
def get_entity_types():
    """Get list of supported entity types"""
    entity_types = {
        'visual_entities': [
            'PERSON', 'BODY_PART', 'EXPRESSION', 'TEXT_REGION', 'OBJECT'
        ],
        'text_entities': [
            'PERSON', 'ORG', 'GPE', 'DATE', 'MONEY', 'PERCENT', 
            'CARDINAL', 'ORDINAL', 'LOC', 'EVENT', 'FAC', 'LANGUAGE',
            'LAW', 'NORP', 'PRODUCT', 'WORK_OF_ART'
        ]
    }
    return jsonify(entity_types)

if __name__ == '__main__':
    # Create necessary directories
    create_upload_dir()
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("Starting NER Web Application...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

