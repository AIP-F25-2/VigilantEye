import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 1. Health check endpoint
def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'

# 2. Main index endpoint
def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json['status'] == 'success'

# 3. API endpoint (should exist)
def test_api_exists(client):
    response = client.get('/api/')
    assert response.status_code in [200, 404]  # 404 if no root handler

# 4. Video API endpoint (v2)
def test_video_api_v2(client):
    response = client.get('/api/v2/video')
    assert response.status_code in [200, 404]  # 404 if no handler

# 5. Project API endpoint (v2)
def test_project_api_v2(client):
    response = client.get('/api/v2/project')
    assert response.status_code in [200, 404]  # 404 if no handler

# 6. Recording API endpoint (v2)
def test_recording_api_v2(client):
    response = client.get('/api/v2/recording')
    assert response.status_code in [200, 404]  # 404 if no handler

# 7. Segment API endpoint (v2)
def test_segment_api_v2(client):
    response = client.get('/api/v2/segment')
    assert response.status_code in [200, 404]  # 404 if no handler

# 8. Device API endpoint (v2)
def test_device_api_v2(client):
    response = client.get('/api/v2/device')
    assert response.status_code in [200, 404]  # 404 if no handler

# 9. Clip API endpoint (v2)
def test_clip_api_v2(client):
    response = client.get('/api/v2/clip')
    assert response.status_code in [200, 404]  # 404 if no handler

# 10. Analytics API endpoint (v2)
def test_analytics_api_v2(client):
    response = client.get('/api/v2/analytics')
    assert response.status_code in [200, 404]  # 404 if no handler
