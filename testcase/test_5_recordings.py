"""
Test Case 5: Recording Management Tests
Tests recording operations, status management, and recording controls
"""
import pytest
from unittest.mock import patch
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


def test_5_1_get_all_recordings(client):
    """Test getting all recordings"""
    response = client.get('/api/v2/recordings')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert isinstance(result['data'], list)
    assert 'pagination' in result


def test_5_2_get_recordings_with_pagination(client):
    """Test getting recordings with pagination"""
    response = client.get('/api/v2/recordings?page=1&per_page=10')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['pagination']['page'] == 1
    assert result['pagination']['per_page'] == 10


def test_5_3_get_recording_by_id_not_found(client):
    """Test getting non-existent recording"""
    response = client.get('/api/v2/recordings/99999')
    assert response.status_code == 404


def test_5_4_start_recording_validation(client):
    """Test starting recording with validation"""
    # Missing required fields
    response = client.post('/api/v2/recordings/start', json={}, content_type='application/json')
    assert response.status_code == 400
    
    # Invalid mode
    data = {
        "mode": "invalid_mode",
        "source": "test"
    }
    response = client.post('/api/v2/recordings/start', json=data, content_type='application/json')
    assert response.status_code == 400


def test_5_5_filter_recordings_by_user(client):
    """Test filtering recordings by user ID"""
    response = client.get('/api/v2/recordings?user_id=1')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_5_6_filter_recordings_by_project(client):
    """Test filtering recordings by project ID"""
    response = client.get('/api/v2/recordings?project_id=1')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_5_7_filter_recordings_by_status(client):
    """Test filtering recordings by status"""
    response = client.get('/api/v2/recordings?status=recording')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_5_8_stop_recording_not_found(client):
    """Test stopping non-existent recording"""
    response = client.post('/api/v2/recordings/99999/stop', content_type='application/json')
    assert response.status_code == 404
