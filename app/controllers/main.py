from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from functools import wraps

main_bp = Blueprint('main', __name__)

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    """Home page"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@main_bp.route('/videos')
@login_required
def videos():
    """Videos page"""
    return render_template('videos.html')

@main_bp.route('/projects')
@login_required
def projects():
    """Projects page"""
    return render_template('projects.html')

@main_bp.route('/recordings')
@login_required
def recordings():
    """Recordings page"""
    return render_template('recordings.html')

@main_bp.route('/health')
def health():
    """Health check endpoint - API"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is operational'
    })
