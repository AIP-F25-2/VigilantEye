"""
Test Case 2: User Management Tests
Tests user CRUD operations and user data validation

NOTE: Test credentials below are for testing purposes only and are not used in production.
"""
import pytest
from app import create_app
from testcase.test_constants import TEST_PASSWORD, TEST_SHORT_PASSWORD


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


@pytest.fixture
def sample_user(client):
    """Create a sample user for testing"""
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": TEST_PASSWORD
    }
    response = client.post('/api/v1/users', json=data, content_type='application/json')
    if response.status_code == 201:
        return response.get_json()['data']
    return None


def test_2_1_create_user_success(client):
    """Test creating a new user"""
    data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": TEST_PASSWORD
    }
    response = client.post('/api/v1/users', json=data, content_type='application/json')
    
    assert response.status_code == 201
    result = response.get_json()
    assert result['status'] == 'success'
    assert result['data']['username'] == data['username']
    assert result['data']['email'] == data['email']


def test_2_2_get_all_users(client, sample_user):
    """Test getting all users"""
    response = client.get('/api/v1/users')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert isinstance(result['data'], list)
    assert len(result['data']) >= 1


def test_2_3_get_user_by_id(client, sample_user):
    """Test getting a specific user by ID"""
    user_id = sample_user['id']
    response = client.get(f'/api/v1/users/{user_id}')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert result['data']['id'] == user_id


def test_2_4_get_user_not_found(client):
    """Test getting non-existent user"""
    response = client.get('/api/v1/users/99999')
    assert response.status_code == 404


def test_2_5_update_user(client, sample_user):
    """Test updating user information"""
    user_id = sample_user['id']
    update_data = {
        "username": "updateduser",
        "email": "updated@example.com"
    }
    response = client.put(f'/api/v1/users/{user_id}', json=update_data, content_type='application/json')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['data']['username'] == update_data['username']


def test_2_6_delete_user(client, sample_user):
    """Test deleting a user"""
    user_id = sample_user['id']
    response = client.delete(f'/api/v1/users/{user_id}')
    
    assert response.status_code == 200
    
    # Verify user is deleted
    get_response = client.get(f'/api/v1/users/{user_id}')
    assert get_response.status_code == 404


def test_2_7_create_user_validation_errors(client):
    """Test user creation validation errors"""
    # Missing required fields
    response = client.post('/api/v1/users', json={}, content_type='application/json')
    assert response.status_code == 400
    
    # Invalid email format - test validation with password field
    # Note: "password" here is a JSON field name, not a credential value
    response = client.post('/api/v1/users', json={
        "username": "test",
        "email": "invalid-email",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }, content_type='application/json')
    assert response.status_code == 400
    
    # Password too short - testing validation rules
    response = client.post('/api/v1/users', json={
        "username": "test",
        "email": "test@example.com",
        "password": TEST_SHORT_PASSWORD  # Test value for validation testing
    }, content_type='application/json')
    assert response.status_code == 400
