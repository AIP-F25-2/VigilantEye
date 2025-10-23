"""
Pytest configuration and fixtures for VigilantEye backend tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app
from src.database.base import Base
from src.database.session import get_db
from src.config.settings import get_settings


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=test_engine
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "role": "user"
    }


@pytest.fixture
def test_admin_data():
    """Sample admin user data for testing."""
    return {
        "username": "testadmin",
        "email": "admin@example.com",
        "password": "adminpassword123",
        "role": "admin"
    }


@pytest.fixture
def test_video_data():
    """Sample video data for testing."""
    return {
        "title": "Test Video",
        "description": "Test video description",
        "filename": "test_video.mp4",
        "file_size": 1024000,
        "duration": 30.5,
        "resolution": "1920x1080",
        "fps": 30
    }


@pytest.fixture
def test_ticket_data():
    """Sample ticket data for testing."""
    return {
        "title": "Test Threat Detection",
        "description": "Test threat detected in video",
        "priority": "high",
        "status": "open",
        "threat_type": "suspicious_activity",
        "confidence_score": 0.85
    }


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = get_settings()
    settings.JWT_SECRET_KEY = "test-secret-key"
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    return settings
