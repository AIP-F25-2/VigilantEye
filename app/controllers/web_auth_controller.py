from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from app.utils.auth_utils import create_user, verify_password

web_auth_bp = Blueprint('web_auth', __name__)

@web_auth_bp.route('/')
def index():
    """Home page"""
    if 'user_id' in session:
        return redirect(url_for('web_auth.dashboard'))
    return render_template('index.html')

@web_auth_bp.route('/dashboard')
def dashboard():
    """Dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('dashboard_enhanced.html')

@web_auth_bp.route('/videos')
def videos():
    """Videos page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('videos.html')

@web_auth_bp.route('/projects')
def projects():
    """Projects page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('projects.html')

@web_auth_bp.route('/recordings')
def recordings():
    """Recordings page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('recordings.html')

@web_auth_bp.route('/cameras')
def cameras():
    """Cameras page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('cameras.html')

@web_auth_bp.route('/security')
def security():
    """Security dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('security_dashboard.html')

@web_auth_bp.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

@web_auth_bp.route('/live-cameras')
def live_cameras():
    """Live cameras page"""
    if 'user_id' not in session:
        return redirect(url_for('web_auth.login'))
    return render_template('live_cameras.html')

@web_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Please provide email and password', 'error')
                return render_template('auth/login.html')
            
            # Verify credentials
            user_data = verify_password(email, password)
            if not user_data:
                flash('Invalid email or password', 'error')
                return render_template('auth/login.html')
            
            # Set session
            session['user_id'] = user_data['id']
            session['email'] = user_data['email']
            session['username'] = user_data.get('username', email.split('@')[0])
            session['roles'] = user_data.get('roles', [])
            
            flash('Login successful!', 'success')
            return redirect(url_for('web_auth.dashboard'))
            
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')


@web_auth_bp.route('/register', methods=['GET', 'POST'])  
def register():
    """Registration page and handler"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            username = request.form.get('username')
            confirm_password = request.form.get('confirm_password')
            
            # Validate inputs
            if not all([email, password, username]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('auth/register.html')
            
            # Create user
            user_data = create_user(
                email=email,
                password=password,
                username=username,
                roles=['operator'],
                site_id='default'
            )
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('web_auth.login'))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html')
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')


@web_auth_bp.route('/logout')
def logout():
    """Logout handler"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('web_auth.index'))
