"""Authentication controller."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.dto.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignUpRequest,
    TokenResponse,
    UserResponse,
)
from src.utils.exceptions import ConflictException, UnauthorizedException
from src.utils.logger import get_logger

from .dependencies import AuthServiceDep, CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up new user",
    description="Register a new user account with STAFF role by default",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Email or username already exists"},
        422: {"description": "Validation error"},
    }
)
async def sign_up(
    request: SignUpRequest,
    auth_service: AuthServiceDep,
):
    """
    Sign up endpoint.
    
    Creates a new user account with the following:
    - Default role: STAFF
    - Email must be unique
    - Username must be unique
    - Password must meet complexity requirements
    
    Returns access and refresh tokens.
    """
    try:
        user, tokens = await auth_service.sign_up(request)
        logger.info(f"User signed up successfully: {user.email}")
        return tokens
    except ConflictException as e:
        logger.warning(f"Sign up conflict: {e.message}")
        raise


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user and return access tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
    }
)
async def login(
    request: LoginRequest,
    auth_service: AuthServiceDep,
):
    """
    Login endpoint.
    
    Authenticates user with email and password.
    Returns access and refresh tokens on successful authentication.
    
    The access token should be included in subsequent requests in the Authorization header:
    `Authorization: Bearer <access_token>`
    """
    try:
        logger.info(f"Login attempt received for email: {request.email}")
        user, tokens = await auth_service.login(request)
        logger.info(f"User logged in successfully: {user.email}")
        return tokens
    except UnauthorizedException as e:
        logger.warning(f"Login failed: {e.message}")
        raise


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate new access token using refresh token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep,
):
    """
    Refresh token endpoint.
    
    Use a valid refresh token to obtain a new access token.
    This allows users to maintain their session without logging in again.
    """
    try:
        tokens = await auth_service.refresh_access_token(request.refresh_token)
        return tokens
    except UnauthorizedException as e:
        logger.warning(f"Token refresh failed: {e.message}")
        raise


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get authenticated user information using access token",
    responses={
        200: {"description": "User information retrieved"},
        401: {"description": "Invalid or expired token"},
    }
)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    Authenticate endpoint - Get current user.
    
    Returns information about the currently authenticated user.
    Requires valid access token in Authorization header.
    
    Example:
    ```
    GET /api/auth/me
    Authorization: Bearer <access_token>
    ```
    """
    # Convert user permissions based on role
    permissions = []
    if current_user.role.value == "ADMIN":
        permissions = [
            "users:read",
            "users:write",
            "users:delete",
            "admin:access",
        ]
    else:  # STAFF
        permissions = [
            "users:read",
        ]

    return CurrentUserResponse(
        user=UserResponse.model_validate(current_user),
        permissions=permissions,
    )


@router.get(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify token",
    description="Verify if the access token is valid",
    responses={
        200: {"description": "Token is valid"},
        401: {"description": "Invalid or expired token"},
    }
)
async def verify_token(current_user: CurrentUser):
    """
    Verify token endpoint.
    
    Checks if the provided access token is valid.
    Returns basic success message if token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
    }
