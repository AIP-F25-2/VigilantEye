from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import User
from database import create_database, init_database
from config import Config
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize database
create_database()
init_database()

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session

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
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
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
        if User.find_by_username(username):
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        if User.find_by_email(email):
            flash('Email already exists', 'error')
            return render_template('signup.html')
        
        # Create new user
        password_hash = User.hash_password(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=password_hash)
        
        if user.save():
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error creating account. Please try again.', 'error')
    
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
    
    user = User.find_by_username(username)
    return jsonify({'available': user is None, 'message': 'Username is available' if user is None else 'Username already exists'})

@app.route('/api/check-email')
def check_email():
    """API endpoint to check if email is available"""
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'available': False, 'message': 'Email is required'})
    
    if not is_valid_email(email):
        return jsonify({'available': False, 'message': 'Invalid email format'})
    
    user = User.find_by_email(email)
    return jsonify({'available': user is None, 'message': 'Email is available' if user is None else 'Email already exists'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
