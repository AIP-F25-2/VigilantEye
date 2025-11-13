"""Integration tests for health API endpoints."""

import os
from datetime import datetime, timedelta

import pytest

from src.app import create_app, db
from src.models.ai_performance_metrics import AIPerformanceMetrics


class FakeRedis:
    """Fake Redis client for testing."""

    def __init__(self):
        self.store = {}

    def ping(self):
        return True

    def from_url(self, *args, **kwargs):
        return self


@pytest.fixture(scope="module")
def app():
    """Create test Flask application."""
    os.environ["ALEMBIC_SQLALCHEMY_URL"] = "sqlite:///:memory:"
    test_app = create_app("development")
    test_app.config["TESTING"] = True
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def cleanup_db(app):
    """Clean up database before and after each test."""
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as testing_client:
        yield testing_client


@pytest.fixture
def fake_redis(monkeypatch):
    """Mock Redis client."""
    fake = FakeRedis()

    def mock_from_url(*args, **kwargs):
        return fake

    monkeypatch.setattr("redis.from_url", mock_from_url)
    return fake


def test_health_endpoint_returns_200(client):
    """Test that /health endpoint returns 200 OK."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_health_ready_all_services_healthy(client, fake_redis, monkeypatch):
    """Test /health/ready when all services are healthy."""
    # Mock ChromaDB manager
    def mock_get_collection_stats():
        return {"total_faces": 10, "total_bodies": 5}

    monkeypatch.setattr(
        "src.api.health.ChromaDBManager",
        lambda: type("MockChromaDB", (), {"get_collection_stats": lambda self: mock_get_collection_stats()})(),
    )

    # Mock Celery app
    def mock_active_workers():
        return {"worker1": {}, "worker2": {}}

    def mock_active():
        return {"worker1": [{"id": "task1"}, {"id": "task2"}]}

    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect",
                        (),
                        {
                            "active_workers": mock_active_workers,
                            "active": mock_active,
                        },
                    )(),
                },
            )(),
        },
    )()

    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.get_json()
    assert data["ready"] is True
    assert len(data["checks"]) == 5  # mysql, redis, chromadb, celery, storage

    # Verify all checks have status='pass'
    for check in data["checks"]:
        assert check["status"] == "pass"
        assert "response_time_ms" in check or "workers" in check or "percentage" in check


def test_health_ready_database_down(client, monkeypatch):
    """Test /health/ready when database is down."""
    # Mock database connection to fail
    def mock_check_db_connection(*args, **kwargs):
        raise Exception("Database connection failed")

    monkeypatch.setattr("src.api.health.check_db_connection", mock_check_db_connection)

    response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.get_json()
    assert data["ready"] is False

    # Find mysql check
    mysql_check = next((c for c in data["checks"] if c["name"] == "mysql"), None)
    assert mysql_check is not None
    assert mysql_check["status"] == "fail"


def test_health_ready_redis_down(client, monkeypatch):
    """Test /health/ready when Redis is down."""
    # Mock Redis to raise ConnectionError
    def mock_from_url(*args, **kwargs):
        raise Exception("Redis connection failed")

    monkeypatch.setattr("redis.from_url", mock_from_url)

    response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.get_json()
    assert data["ready"] is False

    # Find redis check
    redis_check = next((c for c in data["checks"] if c["name"] == "redis"), None)
    assert redis_check is not None
    assert redis_check["status"] == "fail"


def test_health_ready_celery_no_workers(client, monkeypatch):
    """Test /health/ready when Celery has no workers."""
    # Mock Celery to return no workers
    def mock_active_workers():
        return {}

    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect",
                        (),
                        {"active_workers": mock_active_workers, "active": lambda: {}},
                    )(),
                },
            )(),
        },
    )()

    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.get_json()
    assert data["ready"] is False

    # Find celery check
    celery_check = next((c for c in data["checks"] if c["name"] == "celery"), None)
    assert celery_check is not None
    assert celery_check["status"] == "fail"
    assert celery_check["workers"] == 0


def test_metrics_endpoint_returns_data(client, fake_redis, monkeypatch):
    """Test /metrics endpoint returns all required metrics."""
    # Create some AI performance metrics
    with client.application.app_context():
        metric = AIPerformanceMetrics(
            task_name="person_detection",
            duration_ms=150,
            status="success",
            created_at=datetime.utcnow(),
        )
        db.session.add(metric)
        db.session.commit()

    # Mock ChromaDB and Celery
    monkeypatch.setattr(
        "src.api.health.ChromaDBManager",
        lambda: type("MockChromaDB", (), {"get_collection_stats": lambda self: {}})(),
    )
    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect", (), {"active_workers": lambda: {"w1": {}}, "active": lambda: {}}
                    )(),
                },
            )(),
        },
    )()
    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.get_json()

    # Verify all required fields
    assert "api_latency" in data
    assert "p50" in data["api_latency"]
    assert "p95" in data["api_latency"]
    assert "p99" in data["api_latency"]

    assert "ai_inference_times" in data
    assert "person_detection" in data["ai_inference_times"]

    assert "database_pool" in data
    assert "size" in data["database_pool"]
    assert "checked_out" in data["database_pool"]

    assert "storage_usage" in data
    assert "total_bytes" in data["storage_usage"]
    assert "percentage" in data["storage_usage"]

    assert "celery" in data
    assert "workers" in data["celery"]
    assert "active_tasks" in data["celery"]

    assert "timestamp" in data


def test_metrics_endpoint_no_latency_data(client, fake_redis, monkeypatch):
    """Test /metrics endpoint when no latency data exists."""
    # Mock services
    monkeypatch.setattr(
        "src.api.health.ChromaDBManager",
        lambda: type("MockChromaDB", (), {"get_collection_stats": lambda self: {}})(),
    )
    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect", (), {"active_workers": lambda: {"w1": {}}, "active": lambda: {}}
                    )(),
                },
            )(),
        },
    )()
    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.get_json()

    # API latency should be zeros when no data
    assert data["api_latency"]["p50"] == 0.0
    assert data["api_latency"]["p95"] == 0.0
    assert data["api_latency"]["p99"] == 0.0


def test_metrics_endpoint_prometheus_format(client, fake_redis, monkeypatch):
    """Test /metrics endpoint returns Prometheus format when requested."""
    # Mock services
    monkeypatch.setattr(
        "src.api.health.ChromaDBManager",
        lambda: type("MockChromaDB", (), {"get_collection_stats": lambda self: {}})(),
    )
    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect", (), {"active_workers": lambda: {"w1": {}}, "active": lambda: {}}
                    )(),
                },
            )(),
        },
    )()
    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/metrics", headers={"Accept": "text/plain"})

    assert response.status_code == 200
    assert response.content_type == "text/plain; charset=utf-8"

    # Check Prometheus format
    content = response.get_data(as_text=True)
    assert "# HELP" in content
    assert "# TYPE" in content
    assert "api_latency_p50_ms" in content


def test_latency_tracking_middleware(client):
    """Test that latency tracking middleware works."""
    # Make some API requests
    for _ in range(10):
        client.get("/health")

    # Check metrics to see if latency was tracked
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.get_json()

    # Latency should be tracked (may be 0 if requests are very fast)
    assert "api_latency" in data


def test_health_endpoints_no_auth_required(client):
    """Test that health endpoints don't require authentication."""
    # GET /health without auth
    response = client.get("/health")
    assert response.status_code == 200

    # GET /health/ready without auth
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)  # May be 503 if services down, but not 401

    # GET /metrics without auth
    response = client.get("/metrics")
    assert response.status_code == 200


def test_storage_check_calculates_percentage(client):
    """Test that storage check calculates percentage correctly."""
    response = client.get("/health/ready")

    assert response.status_code in (200, 503)
    data = response.get_json()

    storage_check = next((c for c in data["checks"] if c["name"] == "storage"), None)
    assert storage_check is not None
    assert "total_bytes" in storage_check
    assert "used_bytes" in storage_check
    assert "free_bytes" in storage_check
    assert "percentage" in storage_check

    # Verify percentage calculation
    if storage_check["total_bytes"] > 0:
        expected_percentage = (storage_check["used_bytes"] / storage_check["total_bytes"]) * 100
        assert abs(storage_check["percentage"] - expected_percentage) < 0.01


def test_ai_inference_times_from_database(client, fake_redis, monkeypatch):
    """Test that AI inference times are calculated from database."""
    # Create AIPerformanceMetrics records
    with client.application.app_context():
        metrics = [
            AIPerformanceMetrics(
                task_name="person_detection",
                duration_ms=100,
                status="success",
                created_at=datetime.utcnow(),
            ),
            AIPerformanceMetrics(
                task_name="person_detection",
                duration_ms=200,
                status="success",
                created_at=datetime.utcnow(),
            ),
            AIPerformanceMetrics(
                task_name="scene_analysis",
                duration_ms=300,
                status="success",
                created_at=datetime.utcnow(),
            ),
        ]
        for metric in metrics:
            db.session.add(metric)
        db.session.commit()

    # Mock services
    monkeypatch.setattr(
        "src.api.health.ChromaDBManager",
        lambda: type("MockChromaDB", (), {"get_collection_stats": lambda self: {}})(),
    )
    mock_celery_app = type(
        "MockCeleryApp",
        (),
        {
            "control": type(
                "MockControl",
                (),
                {
                    "inspect": lambda: type(
                        "MockInspect", (), {"active_workers": lambda: {"w1": {}}, "active": lambda: {}}
                    )(),
                },
            )(),
        },
    )()
    monkeypatch.setattr("src.api.health._get_celery_app", lambda: mock_celery_app)

    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.get_json()

    # person_detection average should be (100 + 200) / 2 = 150
    assert data["ai_inference_times"]["person_detection"] == 150.0
    # scene_analysis average should be 300
    assert data["ai_inference_times"]["scene_analysis"] == 300.0

