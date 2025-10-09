from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import bcrypt
import re
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

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

if __name__ == '__main__':
    print("Starting VIGILANTEye (Demo)...")
    print("Note: This demo uses file-based storage instead of MySQL")
    print("Open your browser and go to: http://localhost:8080")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=8080)
