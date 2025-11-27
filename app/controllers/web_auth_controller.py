from flask import Blueprint, request, render_template, redirect, url_for, session, flash, Markup
from app.utils.auth_utils import create_user, verify_password
from app.models.user import User

web_auth_bp = Blueprint('web_auth', __name__)

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
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')


@web_auth_bp.route('/signup', methods=['GET', 'POST'])
@web_auth_bp.route('/register', methods=['GET', 'POST'])
def signup():
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
    return redirect(url_for('main.index'))


@web_auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page and handler"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            
            if not email:
                flash('Please provide your email address', 'error')
                return render_template('auth/forgot_password.html')
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            # Always show success message for security (don't reveal if email exists)
            if user:
                reset_token = user.generate_reset_token()
                # In a production app, you would send an email here
                # For now, we'll show the reset link (in production, remove this)
                reset_url = url_for('web_auth.reset_password', token=reset_token, _external=True)
                flash(Markup(f'Password reset link generated. <a href="{reset_url}" class="alert-link">Click here to reset your password</a>'), 'info')
            else:
                flash('If an account with that email exists, a password reset link has been sent.', 'info')
            
            return render_template('auth/forgot_password.html')
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/forgot_password.html')
    
    return render_template('auth/forgot_password.html')


@web_auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password page and handler"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    # Find user by reset token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('web_auth.forgot_password'))
    
    # Verify token is valid
    if not user.verify_reset_token(token):
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('web_auth.forgot_password'))
    
    if request.method == 'POST':
        try:
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if not password or not confirm_password:
                flash('Please provide both password fields', 'error')
                return render_template('auth/reset_password.html', token=token)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('auth/reset_password.html', token=token)
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('auth/reset_password.html', token=token)
            
            # Set new password
            user.set_password(password)
            user.clear_reset_token()
            
            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('web_auth.login'))
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/reset_password.html', token=token)
    
    return render_template('auth/reset_password.html', token=token)
