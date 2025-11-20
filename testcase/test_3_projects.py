"""
Test Case 3: Project Management Tests
Tests project CRUD operations, filtering, and project-user relationships

NOTE: Test credentials below are for testing purposes only and are not used in production.
"""
import pytest
from app import create_app
from testcase.test_constants import TEST_PASSWORD


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
    """Create a sample user"""
    data = {
        "username": "projectowner",
        "email": "owner@example.com",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }
    response = client.post('/api/v1/users', json=data, content_type='application/json')
    if response.status_code == 201:
        return response.get_json()['data']
    return None


@pytest.fixture
def sample_project(client, sample_user):
    """Create a sample project"""
    if not sample_user:
        return None
    
    data = {
        "name": "Test Project",
        "description": "A test surveillance project",
        "user_id": sample_user['id'],
        "is_public": False,
        "category": "security"
    }
    response = client.post('/api/v2/projects', 
                          json=data, 
                          content_type='application/json',
                          headers={'X-User-ID': str(sample_user['id'])})
    if response.status_code == 201:
        return response.get_json()['data']
    return None


def test_3_1_create_project_success(client, sample_user):
    """Test creating a new project"""
    data = {
        "name": "New Surveillance Project",
        "description": "Project for testing",
        "user_id": sample_user['id'],
        "is_public": False,
        "category": "security"
    }
    response = client.post('/api/v2/projects', 
                          json=data, 
                          content_type='application/json',
                          headers={'X-User-ID': str(sample_user['id'])})
    
    assert response.status_code == 201
    result = response.get_json()
    assert result['status'] == 'success'
    assert result['data']['name'] == data['name']


def test_3_2_get_all_projects(client, sample_project):
    """Test getting all projects"""
    response = client.get('/api/v2/projects')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert 'pagination' in result
    assert isinstance(result['data'], list)


def test_3_3_get_project_by_id(client, sample_project):
    """Test getting a specific project"""
    project_id = sample_project['id']
    response = client.get(f'/api/v2/projects/{project_id}')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['data']['id'] == project_id


def test_3_4_update_project(client, sample_project):
    """Test updating project information"""
    project_id = sample_project['id']
    update_data = {
        "name": "Updated Project Name",
        "description": "Updated description"
    }
    response = client.put(f'/api/v2/projects/{project_id}', 
                         json=update_data, 
                         content_type='application/json')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['data']['name'] == update_data['name']


def test_3_5_delete_project(client, sample_project):
    """Test deleting a project"""
    project_id = sample_project['id']
    response = client.delete(f'/api/v2/projects/{project_id}')
    
    assert response.status_code == 200
    
    # Verify project is deleted
    get_response = client.get(f'/api/v2/projects/{project_id}')
    assert get_response.status_code == 404


def test_3_6_get_projects_with_filters(client, sample_project):
    """Test getting projects with filters"""
    # Filter by is_public
    response = client.get('/api/v2/projects?is_public=false')
    assert response.status_code == 200
    
    # Filter by user_id
    if sample_project:
        user_id = sample_project.get('owner_id')
        response = client.get(f'/api/v2/projects?user_id={user_id}')
        assert response.status_code == 200


def test_3_7_project_pagination(client):
    """Test project pagination"""
    response = client.get('/api/v2/projects?page=1&per_page=10')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['pagination']['page'] == 1
    assert result['pagination']['per_page'] == 10


def test_3_8_create_project_validation(client):
    """Test project creation validation"""
    # Missing required name
    response = client.post('/api/v2/projects', json={}, content_type='application/json')
    assert response.status_code == 400
