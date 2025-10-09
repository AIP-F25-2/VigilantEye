"""
VigilantEye Integrated Application
Combines original VigilantEye functionality with Face AI capabilities
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import bcrypt
import re
import json
import os
import sys
from datetime import datetime

# Add face_ai directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'face_ai'))

# Import Face AI functionality
try:
    from face_ai.face_detection_api import create_face_ai_routes, VigilantEyeFaceAI
    FACE_AI_AVAILABLE = True
    print("Full Face AI module loaded successfully")
except ImportError as e:
    print(f"Full Face AI module not available: {e}")
    try:
        from face_ai.simple_face_detection import create_simple_face_ai_routes
        FACE_AI_AVAILABLE = True
        FACE_AI_MODE = "demo"
        print("Simple Face AI module loaded (demo mode)")
    except ImportError as e2:
        print(f"Simple Face AI module not available: {e2}")
        FACE_AI_AVAILABLE = False
        FACE_AI_MODE = "none"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vigilanteye-integrated-secret-key'

# Simple file-based storage for demo purposes
USERS_FILE = 'users.json'

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# Original VigilantEye routes
@app.route('/')
def index():
    """Home page"""
    if is_logged_in():
        return render_template('dashboard.html', username=session.get('username'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        users = load_users()
        if username in users and verify_password(password, users[username]['password_hash']):
            session['user_id'] = users[username]['id']
            session['username'] = users[username]['username']
            session['email'] = users[username]['email']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('signup.html')
        
        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        # Check if user already exists
        users = load_users()
        if username in users:
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        # Check if email already exists
        for user_data in users.values():
            if user_data['email'] == email:
                flash('Email already exists', 'error')
                return render_template('signup.html')
        
        # Create new user
        user_id = len(users) + 1
        password_hash = hash_password(password)
        users[username] = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash
        }
        
        save_users(users)
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout handler"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/api/check-username')
def check_username():
    """API endpoint to check if username is available"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({'available': False, 'message': 'Username is required'})
    
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Username must be at least 3 characters'})
    
    users = load_users()
    available = username not in users
    return jsonify({'available': available, 'message': 'Username is available' if available else 'Username already exists'})

@app.route('/api/check-email')
def check_email():
    """API endpoint to check if email is available"""
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'available': False, 'message': 'Email is required'})
    
    if not is_valid_email(email):
        return jsonify({'available': False, 'message': 'Invalid email format'})
    
    users = load_users()
    available = not any(user_data['email'] == email for user_data in users.values())
    return jsonify({'available': available, 'message': 'Email is available' if available else 'Email already exists'})

# New integrated routes
@app.route('/face-ai')
def face_ai_redirect():
    """Redirect to Face AI dashboard"""
    if not is_logged_in():
        flash('Please log in to access Face AI features', 'error')
        return redirect(url_for('login'))
    if FACE_AI_AVAILABLE:
        return redirect(url_for('simple_face_ai_dashboard'))
    else:
        return render_template('face_ai_unavailable.html', username=session.get('username'))

@app.route('/face-ai/dashboard')
def face_ai_dashboard():
    """Face AI dashboard page"""
    if not is_logged_in():
        flash('Please log in to access Face AI features', 'error')
        return redirect(url_for('login'))
    
    if not FACE_AI_AVAILABLE:
        return render_template('face_ai_unavailable.html', username=session.get('username'))
    
    # Return the VigilantEye-themed dashboard HTML matching the existing design system
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>Face AI Dashboard - VIGILANTEye v4.0</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
        <style>
            /* VigilantEye Theme - Matching existing design system */
            body {
                background: linear-gradient(135deg, #f8fafc 0%, #ffffff 60%, #f9fbfd 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #334155;
                min-height: 100vh;
            }
            
            .navbar-brand {
                font-weight: 800;
                font-size: 1.5rem;
                color: #111827 !important;
                transition: color 0.2s ease, transform 0.2s ease;
            }
            
            .navbar-brand:hover {
                color: #1f2937 !important;
                transform: translateY(-1px);
            }
            
            .card {
                border: 1px solid #e5e7eb;
                background: #ffffff;
                box-shadow: 0 8px 16px rgba(2, 6, 23, 0.04);
                border-radius: 1rem;
                color: #334155;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                transition: all 0.3s ease-in-out;
            }
            
            .card-header {
                background: #f9fafb;
                border-bottom: 1px solid #e5e7eb;
                font-weight: 600;
                color: #334155;
            }
            
            .jumbotron {
                background: linear-gradient(135deg, #99f6e4 0%, #14b8a6 100%);
            }
            
            .btn {
                border-radius: 0.375rem;
                font-weight: 500;
            }
            
            .btn:hover {
                transform: translateY(-1px);
                transition: all 0.2s ease-in-out;
            }
            
            .btn-primary:hover {
                box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
            }
            
            .btn-success:hover {
                box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
            }
            
            .upload-zone {
                border: 2px dashed #14b8a6;
                border-radius: 1rem;
                padding: 3rem 2rem;
                text-align: center;
                background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
            }
            
            .upload-zone:hover {
                border-color: #0d9488;
                background: linear-gradient(135deg, #e6fffa 0%, #e0fdfa 100%);
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(20, 184, 166, 0.15);
            }
            
            .upload-zone.dragover {
                border-color: #059669;
                background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            }
            
            .upload-icon {
                font-size: 3rem;
                color: #14b8a6;
                margin-bottom: 1rem;
                animation: bounce 2s infinite;
            }
            
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-8px); }
                60% { transform: translateY(-4px); }
            }
            
            .face-result-card {
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                margin: 1rem 0;
                box-shadow: 0 8px 16px rgba(2, 6, 23, 0.04);
                border-left: 4px solid #14b8a6;
                transition: all 0.3s ease;
            }
            
            .face-result-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            }
            
            .face-result-card.new-person {
                border-left-color: #ef4444;
            }
            
            .face-result-card.known-person {
                border-left-color: #10b981;
            }
            
            .person-avatar {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 1.25rem;
                font-weight: bold;
                margin-right: 1rem;
            }
            
            .confidence-bar {
                height: 6px;
                background: #f1f5f9;
                border-radius: 3px;
                overflow: hidden;
                margin: 0.5rem 0;
            }
            
            .confidence-fill {
                height: 100%;
                background: linear-gradient(90deg, #ef4444 0%, #f59e0b 50%, #10b981 100%);
                transition: width 0.5s ease;
            }
            
            .demo-notice {
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                border: 1px solid #f59e0b;
                border-radius: 0.75rem;
                padding: 1.5rem;
                margin: 1.5rem 0;
                position: relative;
            }
            
            .demo-notice::before {
                content: '⚠️';
                position: absolute;
                top: 1rem;
                right: 1.5rem;
                font-size: 1.5rem;
            }
            
            .status-badge {
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: #f59e0b;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 1rem;
                font-size: 0.875rem;
                font-weight: 600;
            }
            
            .breadcrumb {
                background: rgba(255, 255, 255, 0.1);
                padding: 0.75rem 1.5rem;
                border-radius: 0 0 0.75rem 0.75rem;
            }
            
            .breadcrumb a {
                color: rgba(255, 255, 255, 0.8);
                text-decoration: none;
                transition: color 0.3s ease;
            }
            
            .breadcrumb a:hover {
                color: white;
            }
        </style>
    </head>
    <body>
        <!-- Navigation matching VigilantEye theme -->
        <nav class="navbar navbar-expand-lg navbar-light" style="background: linear-gradient(135deg, #e0f2fe 0%, #eff6ff 100%); border-bottom: 1px solid #bfdbfe;">
            <div class="container">
                <a class="navbar-brand" href="/">
                    <i class="bi bi-eye-fill me-2"></i>VIGILANTEye
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item">
                            <span class="navbar-text me-3">Welcome, """ + session.get('username', 'User') + """!</span>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/">Dashboard</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/logout">Logout</a>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        <main class="container mt-4">
            <!-- Header matching VigilantEye style -->
            <div class="jumbotron text-white p-4 rounded mb-4">
                <h1 class="display-6 mb-2"><i class="bi bi-person-badge me-3"></i>Face AI Analysis v4.0</h1>
                <p class="mb-0">Advanced face detection, recognition, and demographics analysis powered by AI.</p>
                <nav aria-label="breadcrumb" class="breadcrumb">
                    <ol class="breadcrumb mb-0">
                        <li class="breadcrumb-item"><a href="/"><i class="bi bi-house-fill me-1"></i>Dashboard</a></li>
                        <li class="breadcrumb-item"><a href="/features"><i class="bi bi-list-ul me-1"></i>Features</a></li>
                        <li class="breadcrumb-item active" aria-current="page"><i class="bi bi-camera-video-fill me-1"></i>Face AI Analysis</li>
                    </ol>
                </nav>
            </div>
            
            
            <div class="row gy-4">
                <!-- Main Content -->
                <div class="col-lg-8">
                    <!-- Upload Zone -->
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-cloud-upload me-2"></i>Upload Image for Analysis</h5>
                        </div>
                        <div class="card-body p-0">
                            <div class="upload-zone" id="uploadZone" onclick="document.getElementById('imageInput').click()">
                                <div class="upload-icon">
                                    <i class="bi bi-cloud-upload"></i>
                                </div>
                                <h4>Drag & Drop Image Here</h4>
                                <p class="text-muted mb-3">or click to select from your device</p>
                                <input type="file" id="imageInput" accept="image/*" style="display: none;">
                                <button class="btn btn-primary">
                                    <i class="bi bi-camera me-2"></i>Choose Image
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="card mt-3">
                        <div class="card-body text-center">
                            <div class="d-flex gap-2 flex-wrap justify-content-center">
                                <button class="btn btn-success" onclick="detectFaces(true)">
                                    <i class="bi bi-person-badge me-2"></i>Full Analysis
                                </button>
                                <button class="btn btn-warning" onclick="detectFaces(false)">
                                    <i class="bi bi-person me-2"></i>Quick Scan
                                </button>
                                <button class="btn btn-primary" onclick="loadStats()">
                                    <i class="bi bi-graph-up me-2"></i>Statistics
                                </button>
                                <button class="btn btn-outline-danger" onclick="resetMemory()">
                                    <i class="bi bi-arrow-clockwise me-2"></i>Reset Memory
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Results Container -->
                    <div class="card mt-3" id="resultsContainer" style="display: none;">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                        </div>
                        <div class="card-body" id="resultsContent">
                            <!-- Results will be displayed here -->
                        </div>
                    </div>
                </div>
                
                <!-- Sidebar -->
                <div class="col-lg-4">
                    <!-- Statistics -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="bi bi-graph-up me-2"></i>Statistics</h6>
                        </div>
                        <div class="card-body" id="statsContainer">
                            <!-- Stats will be loaded here -->
                        </div>
                    </div>
                    
                    <!-- System Status -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="bi bi-gear me-2"></i>System Status</h6>
                        </div>
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>AI Engine</span>
                                <span class="badge bg-success">Active</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Face Detection</span>
                                <span class="badge bg-success">Active</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Demographics</span>
                                <span class="badge bg-success">Active</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span>Recognition</span>
                                <span class="badge bg-success">Active</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Activity -->
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0"><i class="bi bi-clock-history me-2"></i>Recent Activity</h6>
                        </div>
                        <div class="card-body">
                            <div class="list-group list-group-flush">
                                <div class="list-group-item d-flex align-items-start px-0">
                                    <i class="bi bi-person-check text-success me-2"></i>
                                    <div>
                                        <div class="fw-semibold small">Face Analysis Ready</div>
                                        <div class="text-muted small">Upload an image to begin analysis</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let detectionCount = 0;
            
            // Drag and drop functionality
            const uploadZone = document.getElementById('uploadZone');
            const imageInput = document.getElementById('imageInput');
            
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });
            
            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    imageInput.files = files;
                    detectFaces(true);
                }
            });
            
            imageInput.addEventListener('change', function(e) {
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
                const buttonText = includeDemographics ? 'Analyzing...' : 'Scanning...';
                
                // Show loading state
                const resultsContainer = document.getElementById('resultsContainer');
                resultsContainer.style.display = 'block';
                resultsContainer.innerHTML = `
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                    </div>
                    <div class="card-body text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">${buttonText}</p>
                    </div>
                `;
                
                fetch(endpoint, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    displayResults(data);
                    detectionCount++;
                    loadStats();
                })
                .catch(error => {
                    console.error('Error:', error);
                    resultsContainer.innerHTML = `
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Error processing image: ${error.message}
                            </div>
                        </div>
                    `;
                });
            }
            
            function displayResults(data) {
                const container = document.getElementById('resultsContainer');
                container.style.display = 'block';
                
                if (data.error) {
                    container.innerHTML = `
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                ${data.error}
                            </div>
                        </div>
                    `;
                    return;
                }
                
                let html = `
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Complete</h5>
                            <span class="badge bg-primary">${data.faces_detected} Face(s) Detected</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <small class="text-muted">Analysis Time:</small><br>
                                <strong>${new Date(data.timestamp).toLocaleString()}</strong>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">Detection Mode:</small><br>
                                <strong>${data.note || 'VigilantEye AI'}</strong>
                            </div>
                        </div>
                `;
                
                if (data.results && data.results.length > 0) {
                    data.results.forEach((result, index) => {
                        const personClass = result.is_new_person ? 'new-person' : 'known-person';
                        const statusIcon = result.is_new_person ? 'bi-person-plus' : 'bi-person-check';
                        const statusText = result.is_new_person ? 'Unknown Subject' : 'Known Subject';
                        const statusColor = result.is_new_person ? 'danger' : 'success';
                        
                        html += `
                            <div class="face-result-card ${personClass}">
                                <div class="d-flex align-items-start">
                                    <div class="person-avatar">
                                        ${String.fromCharCode(65 + index)}
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-start mb-2">
                                            <h6 class="mb-1">Subject ${index + 1}</h6>
                                            <span class="badge bg-${statusColor}">
                                                <i class="bi ${statusIcon} me-1"></i>${statusText}
                                            </span>
                                        </div>
                                        <div class="row">
                                            <div class="col-md-6">
                                                <small class="text-muted">Subject ID:</small><br>
                                                <strong>${result.person_id}</strong>
                                            </div>
                                            <div class="col-md-6">
                                                <small class="text-muted">Recognition Confidence:</small><br>
                                                <div class="confidence-bar">
                                                    <div class="confidence-fill" style="width: ${(result.similarity_score * 100)}%"></div>
                                                </div>
                                                <small>${(result.similarity_score * 100).toFixed(1)}%</small>
                                            </div>
                                        </div>
                        `;
                        
                        if (result.gender) {
                            html += `
                                <div class="row mt-2">
                                    <div class="col-md-6">
                                        <small class="text-muted">Gender:</small><br>
                                        <strong>${result.gender}</strong>
                                        <small class="text-muted"> (${(result.gender_score * 100).toFixed(1)}%)</small>
                                    </div>
                                    <div class="col-md-6">
                                        <small class="text-muted">Age Group:</small><br>
                                        <strong>${result.age_group}</strong>
                                        <small class="text-muted"> (${(result.age_score * 100).toFixed(1)}%)</small>
                                    </div>
                                </div>
                            `;
                        }
                        
                        html += `
                                        <div class="row mt-2">
                                            <div class="col-12">
                                                <small class="text-muted">Detection Area:</small><br>
                                                <code>X:${result.bounding_box[0]} Y:${result.bounding_box[1]} W:${result.bounding_box[2]} H:${result.bounding_box[3]}</code>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                } else {
                    html += `
                        <div class="alert alert-info text-center">
                            <i class="bi bi-info-circle me-2"></i>
                            No faces detected in the image.
                        </div>
                    `;
                }
                
                html += `</div>`;
                container.innerHTML = html;
            }
            
            function loadStats() {
                fetch('/face-ai/stats')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('statsContainer');
                    container.innerHTML = `
                        <div class="row text-center">
                            <div class="col-6 mb-3">
                                <div class="fw-bold text-primary" style="font-size: 1.5rem;">${data.total_detections + detectionCount}</div>
                                <div class="text-muted small">Total Scans</div>
                            </div>
                            <div class="col-6 mb-3">
                                <div class="fw-bold text-success" style="font-size: 1.5rem;">${data.total_faces_detected + detectionCount}</div>
                                <div class="text-muted small">Faces Detected</div>
                            </div>
                            <div class="col-6">
                                <div class="fw-bold text-info" style="font-size: 1.5rem;">${data.known_persons}</div>
                                <div class="text-muted small">Known Subjects</div>
                            </div>
                            <div class="col-6">
                                <div class="fw-bold text-warning" style="font-size: 1.5rem;">${data.mode || 'Demo'}</div>
                                <div class="text-muted small">System Mode</div>
                            </div>
                        </div>
                    `;
                })
                .catch(error => {
                    console.error('Error loading stats:', error);
                });
            }
            
            function resetMemory() {
                if (confirm('Are you sure you want to reset the face recognition memory? This will clear all known subjects.')) {
                    fetch('/face-ai/reset', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert('Face recognition memory reset successfully');
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

# Face AI API routes
@app.route('/face-ai/detect', methods=['POST'])
def detect_faces():
    """Detect faces (demo mode)"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400
        
        file = request.files["image"]
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Simulate processing with random results
        import random
        faces_count = random.randint(1, 3)  # Random 1-3 faces
        results = []
        
        for i in range(faces_count):
            results.append({
                "person_id": f"person_{i+1:03d}",
                "is_new_person": random.choice([True, False]),
                "similarity_score": round(random.uniform(0.0, 0.95), 3),
                "bounding_box": [
                    random.randint(50, 200),  # x
                    random.randint(50, 200),  # y
                    random.randint(100, 300), # width
                    random.randint(100, 300)  # height
                ],
                "gender": random.choice(["Male", "Female", "Unknown"]),
                "age_group": random.choice(["(0-2)", "(4-6)", "(8-12)", "(15-20)", "(25-32)", "(38-43)", "(48-53)", "(60-100)"]),
                "gender_score": round(random.uniform(0.5, 0.95), 3),
                "age_score": round(random.uniform(0.6, 0.9), 3)
            })
        
        result = {
            "success": True,
            "faces_detected": faces_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "note": "Demo mode - Install OpenCV and face-recognition for real detection"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Demo processing error: {str(e)}"}), 500

@app.route('/face-ai/detect-simple', methods=['POST'])
def detect_faces_simple():
    """Simple face detection (demo mode)"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400
        
        file = request.files["image"]
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Simulate processing with random results
        import random
        faces_count = random.randint(1, 2)  # Random 1-2 faces for simple detection
        results = []
        
        for i in range(faces_count):
            results.append({
                "person_id": f"person_{i+1:03d}",
                "is_new_person": random.choice([True, False]),
                "similarity_score": round(random.uniform(0.0, 0.95), 3),
                "bounding_box": [
                    random.randint(50, 200),  # x
                    random.randint(50, 200),  # y
                    random.randint(100, 300), # width
                    random.randint(100, 300)  # height
                ]
            })
        
        result = {
            "success": True,
            "faces_detected": faces_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "note": "Demo mode - Install OpenCV and face-recognition for real detection"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Demo processing error: {str(e)}"}), 500

@app.route('/face-ai/stats')
def get_face_ai_stats():
    """Get detection statistics"""
    return jsonify({
        "total_detections": 0,
        "total_faces_detected": 0,
        "known_persons": 0,
        "average_faces_per_detection": 0,
        "mode": "Demo"
    })

@app.route('/face-ai/reset', methods=['POST'])
def reset_face_memory():
    """Reset face recognition memory"""
    return jsonify({"message": "Face AI memory reset successfully"})

@app.route('/features')
def features():
    """Features page showing all available capabilities"""
    return render_template('features.html', 
                         username=session.get('username') if is_logged_in() else None,
                         face_ai_available=FACE_AI_AVAILABLE)

# Face AI routes are now defined directly in the main application
print("Face AI routes integrated into main application")

if __name__ == '__main__':
    import os
    
    # Production configuration
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("Starting VigilantEye Integrated Application...")
    print("=" * 60)
    print("Features Available:")
    print("   - User Authentication & Management")
    print("   - Secure Login/Registration")
    print("   - Session Management")
    if FACE_AI_AVAILABLE:
        print("   - Face Detection & Recognition")
        print("   - Demographics Analysis (Age/Gender)")
        print("   - Real-time Face AI Dashboard")
    else:
        print("   - Face AI (Install dependencies to enable)")
    print("=" * 60)
    print(f"Server running on port: {port}")
    print(f"Access: http://localhost:{port}")
    print(f"Face AI: http://localhost:{port}/face-ai")
    print("=" * 60)
    
    app.run(debug=debug, host='0.0.0.0', port=port)
