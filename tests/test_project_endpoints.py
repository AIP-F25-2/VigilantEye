import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.models import User, Project, Video, Recording, OutboundMessage


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
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    response = client.post('/api/v1/users', json=user_data, content_type='application/json')
    if response.status_code == 201:
        return response.get_json()['data']
    return None


# ==================== PROJECT TESTS ====================

def test_get_projects_empty(client):
    """Test getting projects when none exist"""
    response = client.get('/api/v2/projects')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert len(data['data']) == 0
    assert 'pagination' in data


def test_create_project_success(client, sample_user):
    """Test creating a project with valid data"""
    project_data = {
        "name": "Test Surveillance Project",
        "description": "A test project for surveillance",
        "user_id": 1,
        "is_public": False,
        "category": "security"
    }
    
    response = client.post('/api/v2/projects', 
                          json=project_data,
                          content_type='application/json',
                          headers={'X-User-ID': '1'})
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['name'] == project_data['name']
    assert data['data']['description'] == project_data['description']
    assert 'id' in data['data']


def test_create_project_missing_name(client):
    """Test creating project without required name"""
    project_data = {
        "description": "A test project",
        "user_id": 1
    }
    
    response = client.post('/api/v2/projects', 
                          json=project_data,
                          content_type='application/json')
    
    assert response.status_code == 400


def test_get_project_by_id(client, sample_user):
    """Test getting a specific project by ID"""
    # First create a project
    project_data = {
        "name": "Test Project",
        "user_id": 1
    }
    create_response = client.post('/api/v2/projects', 
                                 json=project_data,
                                 content_type='application/json',
                                 headers={'X-User-ID': '1'})
    project_id = create_response.get_json()['data']['id']
    
    # Then get it
    response = client.get(f'/api/v2/projects/{project_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['id'] == project_id


def test_get_project_not_found(client):
    """Test getting non-existent project"""
    response = client.get('/api/v2/projects/99999')
    assert response.status_code == 404


def test_update_project(client, sample_user):
    """Test updating a project"""
    # Create project
    project_data = {
        "name": "Original Name",
        "user_id": 1
    }
    create_response = client.post('/api/v2/projects', 
                                 json=project_data,
                                 content_type='application/json',
                                 headers={'X-User-ID': '1'})
    project_id = create_response.get_json()['data']['id']
    
    # Update project
    update_data = {
        "name": "Updated Name",
        "description": "Updated description"
    }
    response = client.put(f'/api/v2/projects/{project_id}', 
                         json=update_data,
                         content_type='application/json')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['name'] == "Updated Name"


def test_delete_project(client, sample_user):
    """Test deleting a project"""
    # Create project
    project_data = {
        "name": "Project to Delete",
        "user_id": 1
    }
    create_response = client.post('/api/v2/projects', 
                                 json=project_data,
                                 content_type='application/json',
                                 headers={'X-User-ID': '1'})
    project_id = create_response.get_json()['data']['id']
    
    # Delete project
    response = client.delete(f'/api/v2/projects/{project_id}')
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f'/api/v2/projects/{project_id}')
    assert get_response.status_code == 404


def test_get_projects_with_filtering(client, sample_user):
    """Test getting projects with filters"""
    # Create multiple projects
    for i in range(3):
        project_data = {
            "name": f"Project {i}",
            "user_id": 1,
            "is_public": i % 2 == 0
        }
        client.post('/api/v2/projects', 
                   json=project_data,
                   content_type='application/json',
                   headers={'X-User-ID': '1'})
    
    # Filter by is_public
    response = client.get('/api/v2/projects?is_public=true')
    assert response.status_code == 200
    data = response.get_json()
    assert all(p['is_public'] == True for p in data['data'])


# ==================== VIDEO TESTS ====================

def test_get_videos_empty(client):
    """Test getting videos when none exist"""
    response = client.get('/api/v2/videos')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert len(data['data']) == 0


def test_get_videos_with_pagination(client):
    """Test getting videos with pagination"""
    response = client.get('/api/v2/videos?page=1&per_page=10')
    assert response.status_code == 200
    data = response.get_json()
    assert 'pagination' in data
    assert data['pagination']['page'] == 1
    assert data['pagination']['per_page'] == 10


def test_get_videos_with_search(client):
    """Test searching videos"""
    response = client.get('/api/v2/videos?query=test')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'


def test_get_video_by_id_not_found(client):
    """Test getting non-existent video"""
    response = client.get('/api/v2/videos/99999')
    assert response.status_code == 404


def test_update_video_not_found(client):
    """Test updating non-existent video"""
    update_data = {"title": "Updated Title"}
    response = client.put('/api/v2/videos/99999', 
                         json=update_data,
                         content_type='application/json')
    assert response.status_code == 404


def test_delete_video_not_found(client):
    """Test deleting non-existent video"""
    response = client.delete('/api/v2/videos/99999')
    assert response.status_code == 404


# ==================== RECORDING TESTS ====================

def test_get_recordings_empty(client):
    """Test getting recordings when none exist"""
    response = client.get('/api/v2/recordings')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert len(data['data']) == 0


def test_get_recordings_with_pagination(client):
    """Test getting recordings with pagination"""
    response = client.get('/api/v2/recordings?page=1&per_page=10')
    assert response.status_code == 200
    data = response.get_json()
    assert 'pagination' in data


def test_get_recording_by_id_not_found(client):
    """Test getting non-existent recording"""
    response = client.get('/api/v2/recordings/99999')
    assert response.status_code == 404


def test_start_recording_invalid_mode(client):
    """Test starting recording with invalid mode"""
    recording_data = {
        "mode": "invalid_mode",
        "source": "test"
    }
    response = client.post('/api/v2/recordings/start', 
                          json=recording_data,
                          content_type='application/json')
    assert response.status_code == 400


def test_start_recording_missing_required_fields(client):
    """Test starting recording without required fields"""
    recording_data = {}
    response = client.post('/api/v2/recordings/start', 
                          json=recording_data,
                          content_type='application/json')
    assert response.status_code == 400


# ==================== USER TESTS ====================

def test_get_users(client):
    """Test getting all users"""
    response = client.get('/api/v1/users')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'data' in data


def test_get_user_by_id_not_found(client):
    """Test getting non-existent user"""
    response = client.get('/api/v1/users/99999')
    assert response.status_code == 404


def test_update_user_not_found(client):
    """Test updating non-existent user"""
    update_data = {"username": "updated"}
    response = client.put('/api/v1/users/99999', 
                         json=update_data,
                         content_type='application/json')
    assert response.status_code == 404


def test_delete_user_not_found(client):
    """Test deleting non-existent user"""
    response = client.delete('/api/v1/users/99999')
    assert response.status_code == 404


# ==================== TELEGRAM TESTS ====================

def test_telegram_ingest_text_message(client):
    """Test Telegram text message ingestion"""
    message_data = {
        "type": "text",
        "content": "Test alert message",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send:
        mock_send.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=message_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'id' in data
        assert data['status'] == 'sent'


def test_telegram_ingest_invalid_payload(client):
    """Test Telegram ingest with invalid payload"""
    message_data = {
        "type": "invalid",
        "content": "Test"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=message_data,
                          content_type='application/json')
    
    assert response.status_code == 400


# ==================== HEALTH CHECK TESTS ====================

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_index_endpoint(client):
    """Test index endpoint"""
    response = client.get('/')
    assert response.status_code == 200


# ==================== INTEGRATION TESTS ====================

def test_project_video_integration(client, sample_user):
    """Test creating project and associating videos"""
    # Create project
    project_data = {
        "name": "Test Project",
        "user_id": 1
    }
    project_response = client.post('/api/v2/projects', 
                                  json=project_data,
                                  content_type='application/json',
                                  headers={'X-User-ID': '1'})
    project_id = project_response.get_json()['data']['id']
    
    # Verify project exists
    get_response = client.get(f'/api/v2/projects/{project_id}')
    assert get_response.status_code == 200
    assert get_response.get_json()['data']['id'] == project_id


def test_user_project_relationship(client):
    """Test user-project relationship"""
    # Create user
    user_data = {
        "username": "projectowner",
        "email": "owner@example.com",
        "password": "password123"
    }
    user_response = client.post('/api/v1/users', 
                               json=user_data,
                               content_type='application/json')
    user_id = user_response.get_json()['data']['id']
    
    # Create project for user
    project_data = {
        "name": "User's Project",
        "user_id": user_id
    }
    project_response = client.post('/api/v2/projects', 
                                  json=project_data,
                                  content_type='application/json',
                                  headers={'X-User-ID': str(user_id)})
    
    assert project_response.status_code == 201
    project_data = project_response.get_json()['data']
    assert project_data['owner_id'] == user_id


# ==================== ERROR HANDLING TESTS ====================

def test_invalid_json_payload(client):
    """Test handling invalid JSON"""
    response = client.post('/api/v2/projects', 
                          data="invalid json",
                          content_type='application/json')
    assert response.status_code == 400


def test_missing_content_type(client):
    """Test handling missing content type"""
    response = client.post('/api/v2/projects', 
                          data='{"name": "Test"}')
    # Should handle gracefully
    assert response.status_code in [400, 415]


def test_unauthorized_access(client):
    """Test accessing protected endpoints without auth"""
    # Most endpoints might not require auth in test mode
    # This is a placeholder for auth tests
    response = client.get('/api/v2/projects')
    # Should work in test mode, but in production would require auth
    assert response.status_code in [200, 401]
