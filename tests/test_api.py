"""
Basic API Tests for VIGILANTEye
"""

import pytest
from app import create_app, db

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_index_page(client):
    """Test homepage loads"""
    response = client.get('/')
    assert response.status_code == 200

def test_login_page(client):
    """Test login page loads"""
    response = client.get('/login')
    assert response.status_code == 200

def test_register_page(client):
    """Test register page loads"""
    response = client.get('/register')
    assert response.status_code == 200

def test_dashboard_requires_auth(client):
    """Test dashboard requires authentication"""
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302  # Redirect to login

