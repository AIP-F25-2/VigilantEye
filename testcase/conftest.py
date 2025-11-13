"""
Pytest configuration file for test cases
This file provides shared fixtures and configuration for all tests
"""
import pytest
from app import create_app, db


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-token'
    app.config['TELEGRAM_WEBHOOK_SECRET'] = 'test-secret'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()
