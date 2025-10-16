import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.models.outbound_message import OutboundMessage, MessageStatus


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-bot-token'
    app.config['TELEGRAM_WEBHOOK_SECRET'] = 'test-secret'
    with app.test_client() as client:
        yield client


# 1. Telegram Ingest Endpoint Tests
def test_telegram_ingest_text_message_success(client):
    """Test successful text message ingestion"""
    sample_data = {
        "type": "text",
        "content": "Test alert message from surveillance system",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {
                "message_id": 12345,
                "chat": {"id": -1001234567890},
                "text": "Test alert message from surveillance system"
            }
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'id' in data
        assert data['status'] == 'sent'
        assert 'telegram' in data
        assert data['telegram']['message_id'] == 12345


def test_telegram_ingest_image_message_success(client):
    """Test successful image message ingestion"""
    sample_data = {
        "type": "image",
        "content": "https://example.com/surveillance-image.jpg",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_photo') as mock_send_photo:
        mock_send_photo.return_value = {
            "ok": True,
            "result": {
                "message_id": 12346,
                "chat": {"id": -1001234567890},
                "photo": []
            }
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'id' in data
        assert data['status'] == 'sent'
        assert 'telegram' in data
        assert data['telegram']['message_id'] == 12346


def test_telegram_ingest_invalid_type(client):
    """Test ingest with invalid message type"""
    sample_data = {
        "type": "invalid_type",
        "content": "Test message",
        "channel_id": "-1001234567890"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid payload'


def test_telegram_ingest_missing_type(client):
    """Test ingest with missing type field"""
    sample_data = {
        "content": "Test message",
        "channel_id": "-1001234567890"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid payload'


def test_telegram_ingest_missing_content(client):
    """Test ingest with missing content field"""
    sample_data = {
        "type": "text",
        "channel_id": "-1001234567890"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid payload'


def test_telegram_ingest_missing_channel_id(client):
    """Test ingest with missing channel_id field"""
    sample_data = {
        "type": "text",
        "content": "Test message"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid payload'


def test_telegram_ingest_empty_content(client):
    """Test ingest with empty content"""
    sample_data = {
        "type": "text",
        "content": "",
        "channel_id": "-1001234567890"
    }
    
    response = client.post('/api/telegram/ingest', 
                          json=sample_data,
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'invalid payload'


def test_telegram_ingest_telegram_api_error(client):
    """Test ingest when Telegram API returns error"""
    sample_data = {
        "type": "text",
        "content": "Test message",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.side_effect = Exception("Telegram API error")
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data['error'] == 'server error'


# 2. Telegram Webhook Tests
def test_telegram_webhook_acknowledge_callback(client):
    """Test webhook callback for acknowledge button press"""
    # First create a message to acknowledge
    sample_data = {
        "type": "text",
        "content": "Test message for acknowledgment",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        # Create message
        create_response = client.post('/api/telegram/ingest', 
                                    json=sample_data,
                                    content_type='application/json')
        assert create_response.status_code == 200
        message_id = create_response.get_json()['id']
        
        # Simulate acknowledge callback
        callback_data = {
            "callback_query": {
                "id": "callback123",
                "data": f"ack:{message_id}",
                "from": {
                    "id": 12345,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "date": 1640995200
            }
        }
        
        with patch('app.services.telegram_client._post') as mock_post:
            mock_post.return_value = {"ok": True}
            
            response = client.post('/webhook/telegram/test-secret', 
                                 json=callback_data,
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['ok'] == True


def test_telegram_webhook_invalid_secret(client):
    """Test webhook with invalid secret"""
    callback_data = {
        "callback_query": {
            "id": "callback123",
            "data": "ack:test-id",
            "from": {"id": 12345}
        }
    }
    
    response = client.post('/webhook/telegram/wrong-secret', 
                          json=callback_data,
                          content_type='application/json')
    
    assert response.status_code == 403
    assert response.data.decode() == "forbidden"


def test_telegram_webhook_unknown_message_ack(client):
    """Test webhook acknowledge for unknown message ID"""
    callback_data = {
        "callback_query": {
            "id": "callback123",
            "data": "ack:unknown-message-id",
            "from": {"id": 12345}
        }
    }
    
    with patch('app.services.telegram_client._post') as mock_post:
        mock_post.return_value = {"ok": True}
        
        response = client.post('/webhook/telegram/test-secret', 
                             json=callback_data,
                             content_type='application/json')
        
        assert response.status_code == 200


def test_telegram_webhook_invalid_callback_data(client):
    """Test webhook with invalid callback data format"""
    callback_data = {
        "callback_query": {
            "id": "callback123",
            "data": "invalid_format",
            "from": {"id": 12345}
        }
    }
    
    response = client.post('/webhook/telegram/test-secret', 
                          json=callback_data,
                          content_type='application/json')
    
    assert response.status_code == 200


# 3. Message Status Tests
def test_message_status_initialization(client):
    """Test that message is created with correct initial status"""
    sample_data = {
        "type": "text",
        "content": "Test message status",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'sent'  # Status should be 'sent' after successful Telegram API call


def test_message_status_acknowledged(client):
    """Test message status change to acknowledged"""
    # Create message
    sample_data = {
        "type": "text",
        "content": "Test acknowledgment",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        create_response = client.post('/api/telegram/ingest', 
                                    json=sample_data,
                                    content_type='application/json')
        message_id = create_response.get_json()['id']
        
        # Acknowledge the message
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
            
            client.post('/webhook/telegram/test-secret', 
                       json=callback_data,
                       content_type='application/json')
            
            # Check that message status is now closed (acknowledged -> closed as per implementation)
            from app import db
            from app.models.outbound_message import OutboundMessage
            msg = OutboundMessage.query.get(message_id)
            assert msg.status == MessageStatus.closed


# 4. Telegram Client Function Tests
def test_build_ack_button():
    """Test building acknowledge button"""
    from app.services.telegram_client import build_ack_button
    
    message_id = "test-message-123"
    button = build_ack_button(message_id)
    
    assert 'inline_keyboard' in button
    assert len(button['inline_keyboard']) == 1
    assert len(button['inline_keyboard'][0]) == 1
    assert button['inline_keyboard'][0][0]['text'] == 'Acknowledge'
    assert button['inline_keyboard'][0][0]['callback_data'] == f'ack:{message_id}'


@patch('requests.post')
def test_send_text_function(mock_post):
    """Test send_text function"""
    from app.services.telegram_client import send_text
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    result = send_text("-1001234567890", "Test message")
    
    assert result == {"ok": True, "result": {"message_id": 123}}
    mock_post.assert_called_once()


@patch('requests.post')
def test_send_photo_function(mock_post):
    """Test send_photo function"""
    from app.services.telegram_client import send_photo
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"message_id": 124}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    result = send_photo("-1001234567890", "https://example.com/image.jpg", "Test caption")
    
    assert result == {"ok": True, "result": {"message_id": 124}}
    mock_post.assert_called_once()


# 5. Edge Cases and Error Handling Tests
def test_telegram_ingest_large_content(client):
    """Test ingest with large content"""
    large_content = "A" * 5000  # Large text content
    
    sample_data = {
        "type": "text",
        "content": large_content,
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200


def test_telegram_ingest_special_characters(client):
    """Test ingest with special characters in content"""
    special_content = "Alert! 🚨 Intrusion detected at Location A. Time: 2024-01-15 14:30:25"
    
    sample_data = {
        "type": "text",
        "content": special_content,
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200


def test_telegram_ingest_invalid_json(client):
    """Test ingest with invalid JSON"""
    response = client.post('/api/telegram/ingest', 
                          data="invalid json",
                          content_type='application/json')
    
    assert response.status_code == 400


def test_telegram_ingest_malformed_channel_id(client):
    """Test ingest with malformed channel ID"""
    sample_data = {
        "type": "text",
        "content": "Test message",
        "channel_id": "invalid-channel-id"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.side_effect = Exception("Invalid chat ID")
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 500


# 6. Database Integration Tests
def test_outbound_message_model_creation():
    """Test OutboundMessage model creation and methods"""
    from app import create_app
    from app import db
    
    app = create_app()
    app.config['TESTING'] = True
    
    with app.app_context():
        # Create message
        msg = OutboundMessage(
            source_type="text",
            content="Test message",
            source_channel="-1001234567890",
            status=MessageStatus.initiated
        )
        
        # Test to_dict method
        msg_dict = msg.to_dict()
        assert msg_dict['source_type'] == "text"
        assert msg_dict['content'] == "Test message"
        assert msg_dict['source_channel'] == "-1001234567890"
        assert msg_dict['status'] == "initiated"
        assert 'id' in msg_dict
        assert 'created_at' in msg_dict


def test_message_status_enum():
    """Test MessageStatus enum values"""
    assert MessageStatus.initiated.value == "initiated"
    assert MessageStatus.sent.value == "sent"
    assert MessageStatus.acknowledged.value == "acknowledged"
    assert MessageStatus.escalated.value == "escalated"
    assert MessageStatus.closed.value == "closed"


# 7. Scheduler Integration Tests (Mocked)
@patch('app.services.scheduler.schedule_post_actions')
def test_scheduler_integration_on_ingest(mock_schedule):
    """Test that scheduler is called when message is ingested"""
    client = create_app().test_client()
    client.application.config['TESTING'] = True
    
    sample_data = {
        "type": "text",
        "content": "Test scheduler integration",
        "channel_id": "-1001234567890"
    }
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {
            "ok": True,
            "result": {"message_id": 12345}
        }
        
        response = client.post('/api/telegram/ingest', 
                              json=sample_data,
                              content_type='application/json')
        
        assert response.status_code == 200
        mock_schedule.assert_called_once()


# 8. Sample Data Test Cases
def test_telegram_ingest_sample_surveillance_alerts(client):
    """Test ingest with realistic surveillance alert messages"""
    sample_alerts = [
        {
            "type": "text",
            "content": "🚨 INTRUSION ALERT 🚨\nLocation: Building A - Main Entrance\nTime: 2024-01-15 14:30:25\nConfidence: 95%",
            "channel_id": "-1001234567890"
        },
        {
            "type": "text",
            "content": "Motion detected in restricted area\nCamera: Cam-03 (Parking Lot)\nDuration: 2 minutes\nStatus: Ongoing",
            "channel_id": "-1001234567890"
        },
        {
            "type": "image",
            "content": "https://example.com/surveillance/alert_20240115_143025.jpg",
            "channel_id": "-1001234567890"
        }
    ]
    
    with patch('app.services.telegram_client.send_text') as mock_send_text, \
         patch('app.services.telegram_client.send_photo') as mock_send_photo:
        
        mock_send_text.return_value = {"ok": True, "result": {"message_id": 12345}}
        mock_send_photo.return_value = {"ok": True, "result": {"message_id": 12346}}
        
        for i, alert_data in enumerate(sample_alerts):
            response = client.post('/api/telegram/ingest', 
                                  json=alert_data,
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'id' in data
            assert data['status'] == 'sent'


def test_telegram_ingest_multiple_channels(client):
    """Test ingest to different channels"""
    channels = ["-1001111111111", "-1002222222222", "-1003333333333"]
    
    with patch('app.services.telegram_client.send_text') as mock_send_text:
        mock_send_text.return_value = {"ok": True, "result": {"message_id": 12345}}
        
        for channel in channels:
            sample_data = {
                "type": "text",
                "content": f"Alert sent to channel {channel}",
                "channel_id": channel
            }
            
            response = client.post('/api/telegram/ingest', 
                                  json=sample_data,
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'id' in data
            assert data['status'] == 'sent'
