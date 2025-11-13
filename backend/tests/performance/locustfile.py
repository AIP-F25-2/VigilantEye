"""Locust performance test suite for VigilantEye API."""

import json
import random
import time
from io import BytesIO

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


class VigilantEyeUser(FastHttpUser):
    """Base user class for VigilantEye API performance tests."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:5000"  # Configurable via --host flag

    def on_start(self):
        """Authenticate user on start."""
        # Login to get access token
        login_data = {
            "username": f"testuser{random.randint(1, 100)}",
            "password": "Password123",
        }
        response = self.client.post("/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            self.client.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # If login fails, try signup
            signup_data = {
                "username": f"testuser{random.randint(1, 1000)}",
                "email": f"test{random.randint(1, 1000)}@example.com",
                "password": "Password123",
            }
            response = self.client.post("/api/auth/signup", json=signup_data)
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("user", {}).get("id")
                # Login after signup
                login_response = self.client.post("/api/auth/login", json=login_data)
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    self.token = login_data.get("access_token")
                    self.client.headers = {"Authorization": f"Bearer {self.token}"}


class VideoUploadUser(VigilantEyeUser):
    """User that uploads videos (weight=30)."""

    weight = 30

    @task(3)
    def upload_video(self):
        """Upload a video file."""
        # Generate random video file (1-10 MB)
        file_size = random.randint(1024 * 1024, 10 * 1024 * 1024)
        video_data = b"fake video data" * (file_size // 16 + 1)
        video_file = ("video", BytesIO(video_data[:file_size]), "video/mp4")

        start_time = time.time()
        response = self.client.post(
            "/api/videos/upload",
            files={"video": video_file},
            headers=self.client.headers,
        )
        upload_time = time.time() - start_time

        if response.status_code == 201:
            self.environment.events.request.fire(
                request_type="POST",
                name="/api/videos/upload",
                response_time=upload_time * 1000,
                response_length=len(response.content),
                exception=None,
            )


class VideoAnalysisUser(VigilantEyeUser):
    """User that analyzes videos (weight=25)."""

    weight = 25
    video_ids = []

    @task(2)
    def list_videos(self):
        """List videos with pagination."""
        response = self.client.get(
            "/api/videos",
            params={"page": 1, "per_page": 20},
            headers=self.client.headers,
        )
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            if videos:
                self.video_ids = [v.get("id") for v in videos]

    @task(3)
    def analyze_video(self):
        """Trigger video analysis."""
        if not self.video_ids:
            self.list_videos()

        if self.video_ids:
            video_id = random.choice(self.video_ids)
            # Trigger analysis
            response = self.client.post(
                f"/api/videos/{video_id}/analyze",
                headers=self.client.headers,
            )
            if response.status_code == 200:
                # Poll for analysis status
                max_polls = 10
                for _ in range(max_polls):
                    status_response = self.client.get(
                        f"/api/videos/{video_id}/analysis-status",
                        headers=self.client.headers,
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get("status") in ["ready", "analyzed", "error"]:
                            break
                    time.sleep(1)


class TicketManagementUser(VigilantEyeUser):
    """User that manages tickets (weight=25)."""

    weight = 25
    ticket_ids = []

    @task(3)
    def list_tickets(self):
        """List tickets with filters."""
        filters = {
            "page": 1,
            "per_page": 20,
            "status": random.choice(["open", "acknowledged", "closed", None]),
        }
        response = self.client.get(
            "/api/tickets",
            params={k: v for k, v in filters.items() if v is not None},
            headers=self.client.headers,
        )
        if response.status_code == 200:
            data = response.json()
            tickets = data.get("tickets", [])
            if tickets:
                self.ticket_ids = [t.get("id") for t in tickets]

    @task(2)
    def view_ticket_details(self):
        """View ticket details."""
        if not self.ticket_ids:
            self.list_tickets()

        if self.ticket_ids:
            ticket_id = random.choice(self.ticket_ids)
            response = self.client.get(
                f"/api/tickets/{ticket_id}",
                headers=self.client.headers,
            )

    @task(1)
    def acknowledge_ticket(self):
        """Acknowledge a ticket."""
        if not self.ticket_ids:
            self.list_tickets()

        if self.ticket_ids:
            ticket_id = random.choice(self.ticket_ids)
            response = self.client.post(
                f"/api/tickets/{ticket_id}/acknowledge",
                headers=self.client.headers,
            )


class ReportDownloadUser(VigilantEyeUser):
    """User that downloads reports (weight=10)."""

    weight = 10
    ticket_ids = []

    def on_start(self):
        """Get ticket IDs on start."""
        super().on_start()
        response = self.client.get(
            "/api/tickets",
            params={"page": 1, "per_page": 10},
            headers=self.client.headers,
        )
        if response.status_code == 200:
            data = response.json()
            tickets = data.get("tickets", [])
            if tickets:
                self.ticket_ids = [t.get("id") for t in tickets]

    @task(1)
    def download_report(self):
        """Download PDF report."""
        if not self.ticket_ids:
            return

        ticket_id = random.choice(self.ticket_ids)
        start_time = time.time()
        response = self.client.get(
            f"/api/tickets/{ticket_id}/report/download",
            params={"format": "pdf"},
            headers=self.client.headers,
        )
        download_time = time.time() - start_time

        if response.status_code == 200:
            # Verify PDF content
            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" in content_type:
                self.environment.events.request.fire(
                    request_type="GET",
                    name="/api/tickets/{id}/report/download",
                    response_time=download_time * 1000,
                    response_length=len(response.content),
                    exception=None,
                )


class MonitoringUser(VigilantEyeUser):
    """User that monitors health endpoints (weight=10)."""

    weight = 10

    @task(2)
    def check_health(self):
        """Check health endpoint."""
        self.client.get("/health")

    @task(1)
    def check_metrics(self):
        """Check metrics endpoint."""
        self.client.get("/metrics", headers=self.client.headers)


# Event handlers
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup test data before test starts."""
    print("Setting up test data...")
    # Create test users, upload videos, create tickets
    # This is handled by the users themselves in on_start()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup and print summary statistics."""
    print("\n=== Performance Test Summary ===")
    stats = environment.stats
    for name, stat in stats.entries.items():
        if stat.num_requests > 0:
            print(
                f"{name}: {stat.num_requests} requests, "
                f"avg={stat.avg_response_time:.2f}ms, "
                f"p95={stat.get_response_time_percentile(0.95):.2f}ms, "
                f"failures={stat.num_failures}"
            )
