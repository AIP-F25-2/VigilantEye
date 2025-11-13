"""
Test Case 4: Video Management Tests
Tests video listing, searching, filtering, and pagination
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


def test_4_1_get_all_videos(client):
    """Test getting all videos"""
    response = client.get('/api/v2/videos')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert isinstance(result['data'], list)
    assert 'pagination' in result


def test_4_2_get_videos_with_pagination(client):
    """Test getting videos with pagination"""
    response = client.get('/api/v2/videos?page=1&per_page=10')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['pagination']['page'] == 1
    assert result['pagination']['per_page'] == 10


def test_4_3_search_videos(client):
    """Test searching videos"""
    response = client.get('/api/v2/videos?query=test')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_4_4_filter_videos_by_status(client):
    """Test filtering videos by status"""
    response = client.get('/api/v2/videos?status=active')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_4_5_filter_videos_by_category(client):
    """Test filtering videos by category"""
    response = client.get('/api/v2/videos?category=surveillance')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_4_6_get_video_by_id_not_found(client):
    """Test getting non-existent video"""
    response = client.get('/api/v2/videos/99999')
    assert response.status_code == 404


def test_4_7_filter_videos_by_duration(client):
    """Test filtering videos by duration"""
    response = client.get('/api/v2/videos?min_duration=60&max_duration=3600')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'


def test_4_8_sort_videos(client):
    """Test sorting videos"""
    response = client.get('/api/v2/videos?sort_by=created_at&sort_order=desc')
    
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
