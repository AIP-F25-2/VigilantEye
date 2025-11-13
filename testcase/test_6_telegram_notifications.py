"""
Test Case 6: Telegram Notification Tests
Tests Telegram message ingestion, webhook handling, and message status
"""
import pytest
from unittest.mock import patch
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-token'
    app.config['TELEGRAM_WEBHOOK_SECRET'] = 'test-secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        from app import db
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_6_1_send_text_message_success(client):
    """Test sending text message to Telegram"""
    data = {
        "type": "text",
        "content": "🚨 INTRUSION ALERT 🚨\nLocation: Building A",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send:
        mock_send.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=data, 
                              content_type='application/json')
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'id' in result
        assert result['status'] == 'sent'


def test_6_2_send_image_message_success(client):
    """Test sending image message to Telegram"""
    data = {
        "type": "image",
        "content": "https://example.com/surveillance/alert.jpg",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_photo') as mock_send:
        mock_send.return_value = {
            "ok": True,
            "result": {"message_id": 12346}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=data, 
                              content_type='application/json')
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['status'] == 'sent'


def test_6_3_telegram_invalid_payload(client):
    """Test Telegram ingest with invalid payload"""
    # Invalid type
    data = {
        "type": "invalid",
        "content": "test",
        "channel_id": "-1001234567890"
    }
    response = client.post('/api/telegram/ingest', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400
    
    # Missing required fields
    data = {"type": "text"}
    response = client.post('/api/telegram/ingest', 
                          json=data, 
                          content_type='application/json')
    assert response.status_code == 400


def test_6_4_webhook_callback_success(client):
    """Test Telegram webhook callback"""
    # First create a message
    message_data = {
        "type": "text",
        "content": "Test message",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send:
        mock_send.return_value = {"ok": True, "result": {"message_id": 12345}}
        create_response = client.post('/api/telegram/ingest', 
                                     json=message_data, 
                                     content_type='application/json')
        message_id = create_response.get_json()['id']
        
        # Test webhook callback
        callback_data = {
            "callback_query": {
                "id": "callback123",
                "data": f"ack:{message_id}",
                "from": {"id": 12345, "first_name": "Test"},
                "date": 1640995200
            }
        }
        
        with patch('app.services.telegram_client._post') as mock_post:
            mock_post.return_value = {"ok": True}
            
            response = client.post('/webhook/telegram/test-secret', 
                                 json=callback_data, 
                                 content_type='application/json')
            
            assert response.status_code == 200
            result = response.get_json()
            assert result['ok'] == True


def test_6_5_webhook_invalid_secret(client):
    """Test webhook with invalid secret"""
    callback_data = {
        "callback_query": {
            "id": "callback123",
            "data": "ack:test-id"
        }
    }
    
    response = client.post('/webhook/telegram/wrong-secret', 
                          json=callback_data, 
                          content_type='application/json')
    assert response.status_code == 403


def test_6_6_telegram_api_error_handling(client):
    """Test error handling when Telegram API fails"""
    data = {
        "type": "text",
        "content": "Test message",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send:
        mock_send.side_effect = Exception("Telegram API error")
        
        response = client.post('/api/telegram/ingest', 
                              json=data, 
                              content_type='application/json')
        
        assert response.status_code == 500
