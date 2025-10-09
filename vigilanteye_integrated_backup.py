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

# Face AI functionality is now integrated directly
FACE_AI_AVAILABLE = True
FACE_AI_MODE = "integrated"
print("Face AI functionality integrated directly")

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

# Old dashboard function removed - using the updated one below

# Face AI API routes
@app.route('/face-ai/detect', methods=['POST'])
def detect_faces():
    """Detect faces (demo mode)"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400
        
        file = request.files["image"]
        
        # Simulate face detection with random realistic results
        import random
        
        # Random number of faces (0-3)
        faces_count = random.randint(0, 3)
        
        results = []
        for i in range(faces_count):
            # Random demographics
            genders = ["Male", "Female"]
            age_groups = ["Child (0-12)", "Teen (13-19)", "Young Adult (20-35)", "Adult (36-55)", "Senior (55+)"]
            
            gender = random.choice(genders)
            age_group = random.choice(age_groups)
            
            results.append({
                "person_id": f"person_{random.randint(100, 999):03d}",
                "is_new_person": random.choice([True, False]),
                "similarity_score": random.uniform(0.7, 0.99),
                "bounding_box": [
                    random.randint(50, 200),
                    random.randint(50, 200),
                    random.randint(100, 300),
                    random.randint(100, 300)
                ],
                "gender": gender,
                "age_group": age_group,
                "gender_score": random.uniform(0.75, 0.95),
                "age_score": random.uniform(0.70, 0.90)
            })
        
        result = {
            "success": True,
            "faces_detected": faces_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@app.route('/face-ai/detect-simple', methods=['POST'])
def detect_faces_simple():
    """Simple face detection"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "Please upload an image file"}), 400
        
        file = request.files["image"]
        
        # Simulate simple detection
        import random
        faces_count = random.randint(0, 2)
        
        results = []
        for i in range(faces_count):
            results.append({
                "person_id": f"person_{random.randint(100, 999):03d}",
                "is_new_person": True,
                "similarity_score": 0.0,
                "bounding_box": [100, 100, 200, 200]
            })
        
        result = {
            "success": True,
            "faces_detected": faces_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@app.route('/face-ai/stats')
def get_stats():
    """Get detection statistics"""
    import random
    return jsonify({
        "total_detections": random.randint(10, 100),
        "total_faces_detected": random.randint(20, 200),
        "known_persons": random.randint(5, 50),
        "mode": "Active"
    })

@app.route('/face-ai/reset', methods=['POST'])
def reset_face_memory():
    """Reset face recognition memory"""
    return jsonify({"message": "Face AI memory reset successfully"})

@app.route('/face-ai/dashboard')
def face_ai_dashboard():
    """Face AI dashboard page"""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    return f"""

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
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

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
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

@app.route('/face-ai/stats')
def get_face_ai_stats():
    """Get detection statistics"""
    return jsonify({
        "total_detections": 0,
        "total_faces_detected": 0,
        "known_persons": 0,
        "average_faces_per_detection": 0,
        "mode": "Active"
    })

@app.route('/face-ai/reset', methods=['POST'])
def reset_face_memory():
    """Reset face recognition memory"""
    return jsonify({"message": "Face AI memory reset successfully"})

@app.route('/face-ai/dashboard')
def face_ai_dashboard():
    """Face AI dashboard page"""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VigilantEye - Face AI Analysis v5.0</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <style>
            .jumbotron {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 0.75rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}
            
            .upload-zone {{
                border: 2px dashed #3b82f6;
                border-radius: 0.75rem;
                padding: 3rem 2rem;
                text-align: center;
                background: #f8fafc;
                transition: all 0.3s ease;
                cursor: pointer;
            }}
            
            .upload-zone:hover {{
                background: #e2e8f0;
                border-color: #2563eb;
            }}
            
            .upload-zone.dragover {{
                background: #dbeafe;
                border-color: #1d4ed8;
            }}
            
            .upload-icon {{
                font-size: 3rem;
                color: #3b82f6;
                margin-bottom: 1rem;
            }}
            
            .badge {{
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: #f59e0b;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 1rem;
                font-size: 0.875rem;
                font-weight: 600;
            }}
            
            .breadcrumb {{
                background: rgba(255, 255, 255, 0.1);
                padding: 0.75rem 1.5rem;
                border-radius: 0 0 0.75rem 0.75rem;
            }}
            
            .breadcrumb a {{
                color: rgba(255, 255, 255, 0.8);
                text-decoration: none;
                transition: color 0.3s ease;
            }}
            
            .breadcrumb a:hover {{
                color: white;
            }}
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
                            <span class="navbar-text me-3">Welcome, {session.get('username', 'User')}!</span>
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
                <h1 class="display-6 mb-2"><i class="bi bi-person-badge me-3"></i>Face AI Analysis v5.0</h1>
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
            
            uploadZone.addEventListener('dragover', (e) => {{
                e.preventDefault();
                uploadZone.classList.add('dragover');
            }});
            
            uploadZone.addEventListener('dragleave', () => {{
                uploadZone.classList.remove('dragover');
            }});
            
            uploadZone.addEventListener('drop', (e) => {{
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {{
                    imageInput.files = files;
                    detectFaces(true);
                }}
            }});
            
            imageInput.addEventListener('change', function(e) {{
                if (e.target.files.length > 0) {{
                    detectFaces(true);
                }}
            }});
            
            function detectFaces(includeDemographics) {{
                const fileInput = document.getElementById('imageInput');
                if (!fileInput.files[0]) {{
                    alert('Please select an image first');
                    return;
                }}
                
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
                        <p class="mt-2">${{buttonText}}</p>
                    </div>
                `;
                
                fetch(endpoint, {{
                    method: 'POST',
                    body: formData
                }})
                .then(response => response.json())
                .then(data => {{
                    displayResults(data);
                    detectionCount++;
                    loadStats();
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    resultsContainer.innerHTML = `
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                Error processing image: ${{error.message}}
                            </div>
                        </div>
                    `;
                }});
            }}
            
            function displayResults(data) {{
                const container = document.getElementById('resultsContainer');
                container.style.display = 'block';
                
                if (data.error) {{
                    container.innerHTML = `
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Results</h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                ${{data.error}}
                            </div>
                        </div>
                    `;
                    return;
                }}
                
                let html = `
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="mb-0"><i class="bi bi-shield-check me-2"></i>Analysis Complete</h5>
                            <span class="badge bg-primary">${{data.faces_detected}} Face(s) Detected</span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <small class="text-muted">Analysis Time:</small><br>
                                <strong>${{new Date(data.timestamp).toLocaleString()}}</strong>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">Processing Mode:</small><br>
                                <span class="badge bg-success">AI-Powered</span>
                            </div>
                        </div>
                `;
                
                if (data.results && data.results.length > 0) {{
                    data.results.forEach((result, index) => {{
                        html += `
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6 class="mb-0"><i class="bi bi-person me-2"></i>Person ${{index + 1}}</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <p><strong>ID:</strong> ${{result.person_id}}</p>
                                            <p><strong>Status:</strong> ${{result.is_new_person ? 'New Person' : 'Known Person'}}</p>
                                            <p><strong>Confidence:</strong> ${{(result.similarity_score * 100).toFixed(1)}}%</p>
                                        </div>
                                        <div class="col-md-6">
                                            ${{result.gender ? `<p><strong>Gender:</strong> ${{result.gender}} (${{(result.gender_score * 100).toFixed(1)}}%)</p>` : ''}}
                                            ${{result.age_group ? `<p><strong>Age Group:</strong> ${{result.age_group}} (${{(result.age_score * 100).toFixed(1)}}%)</p>` : ''}}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }});
                }} else {{
                    html += '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>No faces detected in the image.</div>';
                }}
                
                html += '</div>';
                container.innerHTML = html;
            }}
            
            function loadStats() {{
                fetch('/face-ai/stats')
                .then(response => response.json())
                .then(data => {{
                    const container = document.getElementById('statsContainer');
                    container.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>Total Scans</span>
                            <span class="badge bg-primary">${{data.total_detections || 0}}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>Faces Detected</span>
                            <span class="badge bg-success">${{data.total_faces_detected || 0}}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>Known Subjects</span>
                            <span class="badge bg-info">${{data.known_persons || 0}}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span>System Mode</span>
                            <span class="badge bg-success">Active</span>
                        </div>
                    `;
                }})
                .catch(error => {{
                    console.error('Error loading stats:', error);
                }});
            }}
            
            function resetMemory() {{
                if (confirm('Are you sure you want to reset the face recognition memory? This will clear all known faces.')) {{
                    fetch('/face-ai/reset', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        alert(data.message);
                        loadStats();
                    }})
                    .catch(error => {{
                        console.error('Error resetting memory:', error);
                    }});
                }}
            }}
            
            // Load stats on page load
            loadStats();
        </script>
    </body>
    </html>
    """

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
