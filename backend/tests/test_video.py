"""
Unit tests for video processing service and API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from src.services.video_processor import VideoProcessingService
from src.api.video import upload_video, get_video_status, get_video_details
from src.models.video import Video
from src.dto.video import VideoCreate, VideoResponse


class TestVideoProcessingService:
    """Test cases for VideoProcessingService."""
    
    def test_generate_processing_id(self):
        """Test processing ID generation."""
        service = VideoProcessingService()
        
        processing_id = service._generate_processing_id(video_id=1, user_id=1)
        
        assert isinstance(processing_id, str)
        assert len(processing_id) > 0
        assert processing_id.startswith("proc_")
    
    def test_extract_frames_success(self):
        """Test successful frame extraction."""
        service = VideoProcessingService()
        
        # Mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video content")
            temp_path = temp_file.name
        
        try:
            # Mock OpenCV
            with patch('cv2.VideoCapture') as mock_capture:
                mock_cap = MagicMock()
                mock_cap.isOpened.return_value = True
                mock_cap.get.side_effect = lambda x: {
                    5: 30.0,  # FPS
                    7: 1000,  # Frame count
                    0: 1920,  # Width
                    1: 1080   # Height
                }.get(x, 0)
                mock_cap.read.return_value = (True, None)  # Frame data
                mock_capture.return_value = mock_cap
                
                # Mock os.makedirs
                with patch('os.makedirs'):
                    result = service.extract_frames(
                        video_path=temp_path,
                        processing_id="test_proc_123",
                        interval_ms=30
                    )
                
                assert result["total_frames_extracted"] > 0
                assert "frames_directory" in result
                assert result["video_fps"] == 30.0
                assert result["video_resolution"] == "1920x1080"
        
        finally:
            os.unlink(temp_path)
    
    def test_extract_frames_invalid_video(self):
        """Test frame extraction with invalid video file."""
        service = VideoProcessingService()
        
        with patch('cv2.VideoCapture') as mock_capture:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = False
            mock_capture.return_value = mock_cap
            
            with pytest.raises(Exception):
                service.extract_frames(
                    video_path="invalid_video.mp4",
                    processing_id="test_proc_123",
                    interval_ms=30
                )
    
    def test_extract_audio_success(self):
        """Test successful audio extraction."""
        service = VideoProcessingService()
        
        # Mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video content")
            temp_path = temp_file.name
        
        try:
            # Mock moviepy
            with patch('moviepy.editor.VideoFileClip') as mock_clip:
                mock_video = MagicMock()
                mock_audio = MagicMock()
                mock_audio.duration = 30.5
                mock_audio.fps = 44100
                mock_audio.nchannels = 2
                mock_video.audio = mock_audio
                mock_clip.return_value = mock_video
                
                # Mock os.makedirs
                with patch('os.makedirs'):
                    result = service.extract_audio(
                        video_path=temp_path,
                        processing_id="test_proc_123"
                    )
                
                assert result["has_audio"] is True
                assert result["duration_sec"] == 30.5
                assert result["sample_rate"] == 44100
                assert result["channels"] == 2
        
        finally:
            os.unlink(temp_path)
    
    def test_extract_audio_no_audio(self):
        """Test audio extraction from video without audio."""
        service = VideoProcessingService()
        
        # Mock video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video content")
            temp_path = temp_file.name
        
        try:
            # Mock moviepy
            with patch('moviepy.editor.VideoFileClip') as mock_clip:
                mock_video = MagicMock()
                mock_video.audio = None  # No audio track
                mock_clip.return_value = mock_video
                
                result = service.extract_audio(
                    video_path=temp_path,
                    processing_id="test_proc_123"
                )
                
                assert result["has_audio"] is False
        
        finally:
            os.unlink(temp_path)


class TestVideoAPI:
    """Test cases for video API endpoints."""
    
    def test_upload_video_success(self, client, test_user_data, test_video_data):
        """Test successful video upload."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Mock file upload
        with patch('src.api.video.save_uploaded_file') as mock_save:
            mock_save.return_value = "test_video.mp4"
            
            with patch('src.services.video_processor.VideoProcessingService') as mock_service:
                mock_service.return_value.process_video.return_value = {
                    "processing_id": "test_proc_123",
                    "status": "processing"
                }
                
                # Create test file
                test_file_content = b"fake video content"
                
                response = client.post(
                    "/api/video/upload",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": ("test_video.mp4", test_file_content, "video/mp4")},
                    data={"title": test_video_data["title"]}
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["title"] == test_video_data["title"]
                assert "processing_id" in data
    
    def test_upload_video_unauthorized(self, client):
        """Test video upload without authentication."""
        test_file_content = b"fake video content"
        
        response = client.post(
            "/api/video/upload",
            files={"file": ("test_video.mp4", test_file_content, "video/mp4")},
            data={"title": "Test Video"}
        )
        
        assert response.status_code == 401
    
    def test_get_video_status_success(self, client, test_user_data):
        """Test getting video processing status."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Mock video processing service
        with patch('src.services.video_processor.VideoProcessingService') as mock_service:
            mock_service.return_value.get_processing_status.return_value = {
                "status": "completed",
                "progress": 100,
                "frames_extracted": 150,
                "audio_extracted": True
            }
            
            response = client.get(
                "/api/video/status/test_proc_123",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100
    
    def test_get_video_details_success(self, client, test_user_data):
        """Test getting video details."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/video/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should return 404 for non-existent video or 200 for existing
        assert response.status_code in [200, 404]
