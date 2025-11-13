"""
Test Case 8: Validation and Error Handling Tests
Tests input validation, error responses, and edge cases
"""
import pytest
from app import create_app


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


def test_8_1_invalid_json_payload(client):
    """Test handling invalid JSON payload"""
    response = client.post('/api/v1/users', 
                          data="invalid json", 
                          content_type='application/json')
    assert response.status_code == 400


def test_8_2_missing_content_type(client):
    """Test handling missing content type"""
    response = client.post('/api/v1/users', 
                          data='{"username": "test"}')
    # Should handle gracefully or return 415
    assert response.status_code in [400, 415]


def test_8_3_empty_request_body(client):
    """Test handling empty request body"""
    response = client.post('/api/v1/users', 
                          json={}, 
                          content_type='application/json')
    assert response.status_code == 400


def test_8_4_invalid_email_format(client):
    """Test validation of email format"""
    data = {
        "username": "test",
        "email": "invalid-email-format",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_8_5_password_too_short(client):
    """Test password length validation"""
    data = {
        "username": "test",
        "email": "test@example.com",
        "password": "12345"  # Less than 6 characters
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_8_6_username_too_short(client):
    """Test username length validation"""
    data = {
        "username": "ab",  # Less than 3 characters
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_8_7_special_characters_handling(client):
    """Test handling special characters in input"""
    data = {
        "username": "test_user@123",
        "email": "test+special@example.com",
        "password": "p@ssw0rd!123"
    }
    # Should either accept or reject with proper validation
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code in [201, 400]


def test_8_8_large_payload_handling(client):
    """Test handling of large payloads"""
    large_data = {
        "username": "test",
        "email": "test@example.com",
        "password": "password123",
        "description": "A" * 10000  # Large description
    }
    response = client.post('/api/v1/users', 
                          json=large_data, 
                          content_type='application/json')
    # Should handle gracefully (accept or reject with proper limit)
    assert response.status_code in [201, 400, 413]
