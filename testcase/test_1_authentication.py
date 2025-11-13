"""
Test Case 1: Authentication Tests
Tests user registration, login, and JWT token management

NOTE: Test credentials below are for testing purposes only and are not used in production.
"""
import pytest
from app import create_app

# Test credentials constants (for testing only, not production secrets)
TEST_PASSWORD = "test_password_123"  # Test-only password, not a real credential
TEST_WRONG_PASSWORD = "wrong_test_password"  # Test-only invalid password


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        from app import db
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_1_1_user_registration_success(client):
    """Test successful user registration"""
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": TEST_PASSWORD
    }
    response = client.post('/api/auth/register', json=data, content_type='application/json')
    
    assert response.status_code == 201
    result = response.get_json()
    assert result['email'] == data['email']
    assert 'id' in result


def test_1_2_user_registration_duplicate_email(client):
    """Test registration with duplicate email"""
    data = {
        "username": "user1",
        "email": "duplicate@example.com",
        "password": TEST_PASSWORD
    }
    # First registration
    client.post('/api/auth/register', json=data, content_type='application/json')
    
    # Second registration with same email
    data["username"] = "user2"
    response = client.post('/api/auth/register', json=data, content_type='application/json')
    
    assert response.status_code == 400


def test_1_3_user_login_success(client):
    """Test successful user login"""
    # First register user
    register_data = {
        "username": "logintest",
        "email": "login@example.com",
        "password": TEST_PASSWORD
    }
    client.post('/api/auth/register', json=register_data, content_type='application/json')
    
    # Then login
    login_data = {
        "email": "login@example.com",
        "password": TEST_PASSWORD
    }
    response = client.post('/api/auth/login', json=login_data, content_type='application/json')
    
    assert response.status_code == 200
    result = response.get_json()
    assert 'access_token' in result
    assert 'refresh_token' in result
    assert 'user' in result


def test_1_4_user_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    login_data = {
        "email": "nonexistent@example.com",
        "password": TEST_WRONG_PASSWORD
    }
    response = client.post('/api/auth/login', json=login_data, content_type='application/json')
    
    assert response.status_code == 401
    result = response.get_json()
    assert result['error'] == 'Invalid credentials'


def test_1_5_login_validation_errors(client):
    """Test login validation errors"""
    # Missing email - test validation with password field only
    # Note: "password" here is a JSON field name, not a credential value
    response = client.post(
        '/api/auth/login',
        json={"password": TEST_PASSWORD},  # Test value, not a real credential
        content_type='application/json'
    )
    assert response.status_code == 400
    
    # Missing password field
    response = client.post(
        '/api/auth/login',
        json={"email": "test@example.com"},
        content_type='application/json'
    )
    assert response.status_code == 400
    
    # Invalid email format
    response = client.post(
        '/api/auth/login',
        json={"email": "invalid", "password": TEST_PASSWORD},  # Test value, not a real credential
        content_type='application/json'
    )
    assert response.status_code == 400
