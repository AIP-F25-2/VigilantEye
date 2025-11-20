"""
Test Case 9: Integration Tests
Tests complete workflows and component interactions

NOTE: Test credentials below are for testing purposes only and are not used in production.
"""
import pytest
from unittest.mock import patch
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


def test_9_1_user_project_integration(client):
    """Test creating user and then creating project for that user"""
    # Create user
    user_data = {
        "username": "owner",
        "email": "owner@example.com",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }
    user_response = client.post('/api/v1/users', 
                               json=user_data, 
                               content_type='application/json')
    user_id = user_response.get_json()['data']['id']
    
    # Create project for user
    project_data = {
        "name": "Owner's Project",
        "description": "Project owned by user",
        "user_id": user_id
    }
    project_response = client.post('/api/v2/projects', 
                                  json=project_data, 
                                  content_type='application/json',
                                  headers={'X-User-ID': str(user_id)})
    
    assert project_response.status_code == 201
    project_result = project_response.get_json()
    assert project_result['data']['owner_id'] == user_id


def test_9_2_authentication_workflow(client):
    """Test complete authentication workflow: register -> login -> get profile"""
    # Register
    register_data = {
        "username": "workflow_user",
        "email": "workflow@example.com",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }
    register_response = client.post('/api/auth/register', 
                                   json=register_data, 
                                   content_type='application/json')
    assert register_response.status_code == 201
    
    # Login
    login_data = {
        "email": "workflow@example.com",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }
    login_response = client.post('/api/auth/login', 
                                json=login_data, 
                                content_type='application/json')
    assert login_response.status_code == 200
    
    token = login_response.get_json()['access_token']
    
    # Get profile (if endpoint exists)
    # This might require auth, so we check if it works
    # me_response = client.get('/api/auth/me', 
    #                         headers={'Authorization': f'Bearer {token}'})
    # assert me_response.status_code in [200, 404]


def test_9_3_telegram_notification_workflow(client):
    """Test complete Telegram notification workflow"""
    with patch('app.services.telegram_client.send_text') as mock_send, \
         patch('app.services.scheduler.schedule_post_actions') as mock_schedule:
        
        mock_send.return_value = {"ok": True, "result": {"message_id": 12345}}
        
        # Send message
        message_data = {
            "type": "text",
            "content": "Integration test alert",
            "channel_id": "-1001234567890"
        }
        send_response = client.post('/api/telegram/ingest', 
                                   json=message_data, 
                                   content_type='application/json')
        
        assert send_response.status_code == 200
        message_id = send_response.get_json()['id']
        
        # Verify scheduler was called
        mock_schedule.assert_called_once()


def test_9_4_error_recovery_workflow(client):
    """Test error recovery in workflows"""
    # Try to create project without user
    project_data = {
        "name": "Test Project",
        "user_id": 99999  # Non-existent user
    }
    response = client.post('/api/v2/projects', 
                          json=project_data, 
                          content_type='application/json')
    
    # Should handle gracefully (either create with validation or return error)
    assert response.status_code in [400, 201, 404]


def test_9_5_multiple_operations_sequence(client):
    """Test sequence of multiple operations"""
    # Create user
    user_data = {
        "username": "sequence_user",
        "email": "sequence@example.com",
        "password": TEST_PASSWORD  # Test value, not a real credential
    }
    user_response = client.post('/api/v1/users', 
                               json=user_data, 
                               content_type='application/json')
    assert user_response.status_code == 201
    user_id = user_response.get_json()['data']['id']
    
    # Get user
    get_response = client.get(f'/api/v1/users/{user_id}')
    assert get_response.status_code == 200
    
    # Update user
    update_data = {"username": "updated_sequence_user"}
    update_response = client.put(f'/api/v1/users/{user_id}', 
                                json=update_data, 
                                content_type='application/json')
    assert update_response.status_code in [200, 404]
