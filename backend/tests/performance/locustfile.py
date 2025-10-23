"""
Performance and load testing configuration.
"""

from locust import HttpUser, task, between
import random
import json
import time

class VigilantEyeUser(HttpUser):
    """Simulate user behavior for load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Login and get authentication token."""
        self.login()
    
    def login(self):
        """Login to get authentication token."""
        login_data = {
            "username": f"testuser{random.randint(1, 100)}",
            "password": "testpassword123"
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # If login fails, try to register
            self.register_and_login(login_data)
    
    def register_and_login(self, login_data):
        """Register new user and login."""
        register_data = {
            "username": login_data["username"],
            "email": f"{login_data['username']}@example.com",
            "password": login_data["password"],
            "role": "user"
        }
        
        self.client.post("/api/auth/register", json=register_data)
        response = self.client.post("/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_dashboard(self):
        """Get dashboard data."""
        self.client.get("/api/dashboard", headers=self.headers)
    
    @task(2)
    def get_tickets(self):
        """Get tickets list."""
        self.client.get("/api/tickets", headers=self.headers)
    
    @task(1)
    def get_videos(self):
        """Get videos list."""
        self.client.get("/api/videos", headers=self.headers)
    
    @task(1)
    def upload_video(self):
        """Simulate video upload."""
        # Create a small test file
        test_content = b"fake video content for testing"
        
        files = {"file": ("test_video.mp4", test_content, "video/mp4")}
        data = {"title": f"Test Video {random.randint(1, 1000)}"}
        
        response = self.client.post(
            "/api/video/upload",
            files=files,
            data=data,
            headers=self.headers
        )
        
        if response.status_code == 201:
            self.video_id = response.json()["id"]
    
    @task(1)
    def get_video_status(self):
        """Check video processing status."""
        if hasattr(self, 'video_id'):
            self.client.get(f"/api/video/status/{self.video_id}", headers=self.headers)
    
    @task(1)
    def create_ticket(self):
        """Create a new ticket."""
        ticket_data = {
            "title": f"Test Ticket {random.randint(1, 1000)}",
            "description": "Test ticket description",
            "priority": random.choice(["low", "medium", "high"]),
            "threat_type": "suspicious_activity"
        }
        
        self.client.post("/api/tickets", json=ticket_data, headers=self.headers)
    
    @task(1)
    def get_health_check(self):
        """Get health check."""
        self.client.get("/api/health")

class AdminUser(HttpUser):
    """Simulate admin user behavior."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login as admin."""
        login_data = {
            "username": "admin",
            "password": "adminpassword123"
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(2)
    def get_all_tickets(self):
        """Get all tickets (admin only)."""
        self.client.get("/api/admin/tickets", headers=self.headers)
    
    @task(1)
    def get_system_metrics(self):
        """Get system metrics (admin only)."""
        self.client.get("/api/admin/metrics", headers=self.headers)
    
    @task(1)
    def get_user_management(self):
        """Get user management data (admin only)."""
        self.client.get("/api/admin/users", headers=self.headers)

class VideoProcessingUser(HttpUser):
    """Simulate heavy video processing load."""
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Login."""
        self.login()
    
    def login(self):
        """Login to get authentication token."""
        login_data = {
            "username": f"videouser{random.randint(1, 50)}",
            "password": "testpassword123"
        }
        
        response = self.client.post("/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.register_and_login(login_data)
    
    def register_and_login(self, login_data):
        """Register and login."""
        register_data = {
            "username": login_data["username"],
            "email": f"{login_data['username']}@example.com",
            "password": login_data["password"],
            "role": "user"
        }
        
        self.client.post("/api/auth/register", json=register_data)
        response = self.client.post("/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def upload_large_video(self):
        """Upload large video files."""
        # Simulate larger file upload
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB file
        
        files = {"file": ("large_video.mp4", large_content, "video/mp4")}
        data = {"title": f"Large Video {random.randint(1, 100)}"}
        
        response = self.client.post(
            "/api/video/upload",
            files=files,
            data=data,
            headers=self.headers
        )
        
        if response.status_code == 201:
            self.video_id = response.json()["id"]
    
    @task(2)
    def check_processing_status(self):
        """Check video processing status."""
        if hasattr(self, 'video_id'):
            self.client.get(f"/api/video/status/{self.video_id}", headers=self.headers)
    
    @task(1)
    def get_processing_queue(self):
        """Get processing queue status."""
        self.client.get("/api/video/queue", headers=self.headers)
