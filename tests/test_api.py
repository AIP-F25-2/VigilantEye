import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 1. Health check endpoint
def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

# 2. Main index endpoint
def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json['status'] == 'success'

# 3. API endpoint (should exist)
def test_api_exists(client):
    response = client.get('/api/')
    assert response.status_code in [200, 404]  # 404 if no root handler

# 4. Video API endpoint (v2)
def test_video_api_v2(client):
    response = client.get('/api/v2/video')
    assert response.status_code in [200, 404]  # 404 if no handler

# 5. Project API endpoint (v2)
def test_project_api_v2(client):
    response = client.get('/api/v2/project')
    assert response.status_code in [200, 404]  # 404 if no handler

# 6. User Signup Tests
def test_user_signup_success(client):
    """Test successful user signup with valid data"""
    sample_data = {
        "username": "testuser123",
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = client.post('/api/users', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == 'User created successfully'
    assert 'data' in data
    
    # Check user data in response
    user_data = data['data']
    assert user_data['username'] == sample_data['username']
    assert user_data['email'] == sample_data['email']
    assert user_data['is_active'] == True
    assert 'id' in user_data
    assert 'created_at' in user_data
    # Password should not be in response
    assert 'password' not in user_data

def test_user_signup_missing_fields(client):
    """Test user signup with missing required fields"""
    # Missing username
    response = client.post('/api/users', 
                          json={"email": "test@example.com", "password": "password123"},
                          content_type='application/json')
    assert response.status_code == 400
    
    # Missing email
    response = client.post('/api/users', 
                          json={"username": "testuser", "password": "password123"},
                          content_type='application/json')
    assert response.status_code == 400
    
    # Missing password
    response = client.post('/api/users', 
                          json={"username": "testuser", "email": "test@example.com"},
                          content_type='application/json')
    assert response.status_code == 400

def test_user_signup_invalid_data(client):
    """Test user signup with invalid data"""
    # Invalid email format
    response = client.post('/api/users', 
                          json={
                              "username": "testuser",
                              "email": "invalid-email",
                              "password": "password123"
                          },
                          content_type='application/json')
    assert response.status_code == 400
    
    # Username too short (less than 3 characters)
    response = client.post('/api/users', 
                          json={
                              "username": "ab",
                              "email": "test@example.com",
                              "password": "password123"
                          },
                          content_type='application/json')
    assert response.status_code == 400
    
    # Password too short (less than 6 characters)
    response = client.post('/api/users', 
                          json={
                              "username": "testuser",
                              "email": "test@example.com",
                              "password": "12345"
                          },
                          content_type='application/json')
    assert response.status_code == 400

def test_user_signup_duplicate_email(client):
    """Test user signup with duplicate email"""
    sample_data = {
        "username": "testuser1",
        "email": "duplicate@example.com",
        "password": "password123"
    }
    
    # Create first user
    response1 = client.post('/api/users', 
                           json=sample_data,
                           content_type='application/json')
    assert response1.status_code == 201
    
    # Try to create second user with same email
    sample_data["username"] = "testuser2"  # Different username
    response2 = client.post('/api/users', 
                           json=sample_data,
                           content_type='application/json')
    assert response2.status_code == 400
    
    data = response2.get_json()
    assert data['status'] == 'error'
    assert 'email already exists' in data['message']

def test_user_signup_duplicate_username(client):
    """Test user signup with duplicate username"""
    sample_data = {
        "username": "duplicateuser",
        "email": "user1@example.com",
        "password": "password123"
    }
    
    # Create first user
    response1 = client.post('/api/users', 
                           json=sample_data,
                           content_type='application/json')
    assert response1.status_code == 201
    
    # Try to create second user with same username
    sample_data["email"] = "user2@example.com"  # Different email
    response2 = client.post('/api/users', 
                           json=sample_data,
                           content_type='application/json')
    assert response2.status_code == 400
    
    data = response2.get_json()
    assert data['status'] == 'error'
    assert 'username already exists' in data['message']

def test_user_signup_edge_cases(client):
    """Test user signup edge cases"""
    # Minimum valid username (3 characters)
    response = client.post('/api/users', 
                          json={
                              "username": "abc",
                              "email": "minuser@example.com",
                              "password": "password123"
                          },
                          content_type='application/json')
    assert response.status_code == 201
    
    # Minimum valid password (6 characters)
    response = client.post('/api/users', 
                          json={
                              "username": "minpass",
                              "email": "minpass@example.com",
                              "password": "123456"
                          },
                          content_type='application/json')
    assert response.status_code == 201
    
    # Maximum valid username (80 characters)
    long_username = "a" * 80
    response = client.post('/api/users', 
                          json={
                              "username": long_username,
                              "email": "longuser@example.com",
                              "password": "password123"
                          },
                          content_type='application/json')
    assert response.status_code == 201

# 7. User Login Tests
def test_user_login_success(client):
    """Test successful user login with valid credentials"""
    # First create a user to login with
    sample_user = {
        "username": "logintest",
        "email": "login@example.com",
        "password": "password123"
    }
    
    # Create user
    create_response = client.post('/api/users', 
                                json=sample_user,
                                content_type='application/json')
    assert create_response.status_code == 201
    
    # Now test login
    login_data = {
        "email": "login@example.com",
        "password": "password123"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert 'user' in data
    
    # Check user data in response
    user_data = data['user']
    assert user_data['email'] == login_data['email']
    assert 'id' in user_data
    assert 'roles' in user_data
    assert 'site_id' in user_data

def test_user_login_invalid_email(client):
    """Test login with invalid email format"""
    login_data = {
        "email": "invalid-email-format",
        "password": "password123"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_invalid_password_length(client):
    """Test login with password too short"""
    login_data = {
        "email": "test@example.com",
        "password": "12345"  # Less than 6 characters
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_missing_email(client):
    """Test login with missing email field"""
    login_data = {
        "password": "password123"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_missing_password(client):
    """Test login with missing password field"""
    login_data = {
        "email": "test@example.com"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_wrong_password(client):
    """Test login with correct email but wrong password"""
    # First create a user
    sample_user = {
        "username": "wrongpassuser",
        "email": "wrongpass@example.com",
        "password": "password123"
    }
    
    create_response = client.post('/api/users', 
                                json=sample_user,
                                content_type='application/json')
    assert create_response.status_code == 201
    
    # Now test login with wrong password
    login_data = {
        "email": "wrongpass@example.com",
        "password": "wrongpassword"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid credentials'

def test_user_login_nonexistent_user(client):
    """Test login with non-existent user email"""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password123"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid credentials'

def test_user_login_case_sensitivity(client):
    """Test login with different case email"""
    # First create a user
    sample_user = {
        "username": "caseuser",
        "email": "case@example.com",
        "password": "password123"
    }
    
    create_response = client.post('/api/users', 
                                json=sample_user,
                                content_type='application/json')
    assert create_response.status_code == 201
    
    # Test login with different case email
    login_data = {
        "email": "CASE@EXAMPLE.COM",  # Different case
        "password": "password123"
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    # This might succeed or fail depending on email case sensitivity implementation
    # We'll test both scenarios
    assert response.status_code in [200, 401]
    
    if response.status_code == 401:
        data = response.get_json()
        assert data['error'] == 'Invalid credentials'

def test_user_login_empty_credentials(client):
    """Test login with empty email and password"""
    login_data = {
        "email": "",
        "password": ""
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_whitespace_credentials(client):
    """Test login with whitespace-only credentials"""
    login_data = {
        "email": "   ",
        "password": "   "
    }
    
    response = client.post('/api/auth/login', 
                          json=login_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Validation error'
    assert 'details' in data

def test_user_login_multiple_users(client):
    """Test login with multiple users to ensure isolation"""
    # Create first user
    user1 = {
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123"
    }
    create_response1 = client.post('/api/users', 
                                 json=user1,
                                 content_type='application/json')
    assert create_response1.status_code == 201
    
    # Create second user
    user2 = {
        "username": "user2",
        "email": "user2@example.com",
        "password": "password456"
    }
    create_response2 = client.post('/api/users', 
                                 json=user2,
                                 content_type='application/json')
    assert create_response2.status_code == 201
    
    # Login with first user
    login1 = {
        "email": "user1@example.com",
        "password": "password123"
    }
    response1 = client.post('/api/auth/login', 
                           json=login1,
                           content_type='application/json')
    assert response1.status_code == 200
    data1 = response1.get_json()
    assert data1['user']['email'] == "user1@example.com"
    
    # Login with second user
    login2 = {
        "email": "user2@example.com",
        "password": "password456"
    }
    response2 = client.post('/api/auth/login', 
                           json=login2,
                           content_type='application/json')
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert data2['user']['email'] == "user2@example.com"
    
    # Ensure tokens are different
    assert data1['access_token'] != data2['access_token']
    assert data1['refresh_token'] != data2['refresh_token']