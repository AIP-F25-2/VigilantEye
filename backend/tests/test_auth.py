"""
Unit tests for authentication service and API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.services.auth import AuthService
from src.api.auth import login, register, get_current_user
from src.models.user import User
from src.dto.auth import UserCreate, UserLogin


class TestAuthService:
    """Test cases for AuthService."""
    
    def test_hash_password(self):
        """Test password hashing."""
        auth_service = AuthService()
        password = "testpassword123"
        
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert auth_service.verify_password(password, hashed)
    
    def test_verify_password(self):
        """Test password verification."""
        auth_service = AuthService()
        password = "testpassword123"
        wrong_password = "wrongpassword"
        
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password(wrong_password, hashed)
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        auth_service = AuthService()
        user_id = 1
        username = "testuser"
        
        token = auth_service.create_access_token(user_id, username)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token(self):
        """Test JWT token verification."""
        auth_service = AuthService()
        user_id = 1
        username = "testuser"
        
        token = auth_service.create_access_token(user_id, username)
        payload = auth_service.verify_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["username"] == username
    
    def test_verify_invalid_token(self):
        """Test invalid token verification."""
        auth_service = AuthService()
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException):
            auth_service.verify_token(invalid_token)


class TestAuthAPI:
    """Test cases for authentication API endpoints."""
    
    def test_register_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json=test_user_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data
    
    def test_register_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username."""
        # Register first user
        client.post("/api/auth/register", json=test_user_data)
        
        # Try to register with same username
        response = client.post(
            "/api/auth/register",
            json=test_user_data
        )
        
        assert response.status_code == 400
    
    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # Register user first
        client.post("/api/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_get_current_user_success(self, client, test_user_data):
        """Test getting current user with valid token."""
        # Register and login
        client.post("/api/auth/register", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
