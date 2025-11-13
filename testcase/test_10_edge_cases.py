"""
Test Case 10: Edge Cases and Boundary Tests
Tests edge cases, boundary conditions, and unusual scenarios
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


def test_10_1_very_long_username(client):
    """Test handling very long username"""
    data = {
        "username": "a" * 100,  # Very long username
        "email": "long@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    # Should either accept (if within limits) or reject
    assert response.status_code in [201, 400]


def test_10_2_unicode_characters(client):
    """Test handling Unicode characters in input"""
    data = {
        "username": "测试用户123",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    # Should handle Unicode properly
    assert response.status_code in [201, 400]


def test_10_3_whitespace_only_input(client):
    """Test handling whitespace-only input"""
    data = {
        "username": "   ",
        "email": "   ",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_10_4_null_values(client):
    """Test handling null values"""
    data = {
        "username": None,
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_10_5_negative_ids(client):
    """Test handling negative IDs"""
    response = client.get('/api/v1/users/-1')
    assert response.status_code in [400, 404]


def test_10_6_zero_id(client):
    """Test handling zero ID"""
    response = client.get('/api/v1/users/0')
    assert response.status_code in [400, 404]


def test_10_7_very_large_id(client):
    """Test handling very large ID numbers"""
    response = client.get('/api/v1/users/999999999999')
    assert response.status_code == 404


def test_10_8_sql_injection_attempt(client):
    """Test SQL injection prevention"""
    data = {
        "username": "admin'; DROP TABLE users; --",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    # Should reject or sanitize (but not crash)
    assert response.status_code in [201, 400]
    
    # Verify table still exists by querying
    get_response = client.get('/api/v1/users')
    assert get_response.status_code == 200


def test_10_9_xss_attempt(client):
    """Test XSS prevention in input"""
    data = {
        "username": "<script>alert('xss')</script>",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', 
                          json=data, 
                          content_type='application/json')
    # Should handle or sanitize
    assert response.status_code in [201, 400]


def test_10_10_concurrent_requests(client):
    """Test handling multiple concurrent requests"""
    import threading
    
    results = []
    
    def make_request():
        data = {
            "username": f"user_{threading.current_thread().ident}",
            "email": f"user_{threading.current_thread().ident}@example.com",
            "password": "password123"
        }
        response = client.post('/api/v1/users', 
                              json=data, 
                              content_type='application/json')
        results.append(response.status_code)
    
    threads = [threading.Thread(target=make_request) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All should complete (success or failure, but not crash)
    assert len(results) == 5
    assert all(status in [201, 400, 409] for status in results)
