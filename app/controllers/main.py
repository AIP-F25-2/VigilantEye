from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from functools import wraps

main_bp = Blueprint('main', __name__)

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('web_auth.login'))
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
    return render_template('dashboard.html', username=session.get('username', 'User'))

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@main_bp.route('/faceai')
@login_required
def face_ai_dashboard():
    """FaceAi dashboard page"""
    return render_template('faceai_dashboard.html')

@main_bp.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

@main_bp.route('/cctv')
@login_required
def cctv_dashboard():
    """CCTV Intelligence Dashboard"""
    return render_template('cctv_dashboard.html')

@main_bp.route('/ai-analytics')
@login_required
def ai_analytics_dashboard():
    """AI Analytics Dashboard"""
    return render_template('ai_analytics_dashboard.html')

@main_bp.route('/health')
def health():
    """Health check endpoint - API"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is operational'
    })
