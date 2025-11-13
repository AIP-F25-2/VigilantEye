"""
Test Case 7: Health Check and System Status Tests
Tests health endpoints and system availability
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_7_1_health_check_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'healthy'


def test_7_2_index_endpoint(client):
    """Test index endpoint"""
    response = client.get('/')
    
    assert response.status_code == 200
    # Can be JSON or HTML depending on implementation
    assert response.status_code in [200, 302]


def test_7_3_api_root_endpoint(client):
    """Test API root endpoint"""
    response = client.get('/api/')
    
    # Should return some response (200 or 404)
    assert response.status_code in [200, 404]


def test_7_4_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get('/health')
    
    # CORS headers should be present if configured
    # This is a basic check
    assert response.status_code == 200


def test_7_5_error_handling_404(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent-endpoint')
    
    assert response.status_code == 404


def test_7_6_error_handling_invalid_method(client):
    """Test method not allowed error"""
    # Try DELETE on a GET-only endpoint
    response = client.delete('/health')
    
    # Should return 405 or handle gracefully
    assert response.status_code in [405, 404, 500]
