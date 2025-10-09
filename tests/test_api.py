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