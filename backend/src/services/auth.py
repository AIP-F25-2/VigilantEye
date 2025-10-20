"""Authentication service."""

from datetime import timedelta
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.dto.auth import LoginRequest, SignUpRequest, TokenResponse
from src.models.user import User
from src.repositories.user import UserRepository
from src.utils.exceptions import ConflictException, UnauthorizedException
from src.utils.logger import get_logger
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    verify_token_type,
)

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.user_repository = UserRepository(session)

    async def sign_up(self, request: SignUpRequest) -> Tuple[User, TokenResponse]:
        """
        Register a new user.
        
        Args:
            request: Sign up request data
            
        Returns:
            Tuple of (created user, tokens)
            
        Raises:
            ConflictException: If email or username already exists
        """
        logger.info(f"Sign up attempt for email: {request.email}")

        # Check if email already exists
        if await self.user_repository.exists_by_email(request.email):
            logger.warning(f"Sign up failed: Email already exists - {request.email}")
            raise ConflictException(
                message="Email already registered",
                detail="A user with this email address already exists"
            )

        # Check if username already exists
        if await self.user_repository.exists_by_username(request.username):
            logger.warning(f"Sign up failed: Username already exists - {request.username}")
            raise ConflictException(
                message="Username already taken",
                detail="This username is already in use"
            )

        # Hash password
        hashed_password = hash_password(request.password)

        # Create user with default role STAFF
        user = await self.user_repository.create(
            email=request.email,
            username=request.username,
            hashed_password=hashed_password,
            full_name=request.full_name,
        )

        await self.session.commit()
        logger.info(f"User created successfully: {user.id} - {user.email}")

        # Generate tokens
        tokens = self._generate_tokens(user)

        return user, tokens

    async def login(self, request: LoginRequest) -> Tuple[User, TokenResponse]:
        """
        Authenticate user and generate tokens.
        
        Args:
            request: Login request data
            
        Returns:
            Tuple of (authenticated user, tokens)
            
        Raises:
            UnauthorizedException: If credentials are invalid
        """
        logger.info(f"Login attempt for email: {request.email}")

        # Get user by email
        user = await self.user_repository.get_by_email(request.email)

        if not user:
            logger.warning(f"Login failed: User not found - {request.email}")
            raise UnauthorizedException(
                message="Invalid credentials",
                detail="Email or password is incorrect"
            )

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            logger.warning(f"Login failed: Invalid password - {request.email}")
            raise UnauthorizedException(
                message="Invalid credentials",
                detail="Email or password is incorrect"
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login failed: User inactive - {request.email}")
            raise UnauthorizedException(
                message="Account disabled",
                detail="Your account has been disabled. Please contact support."
            )

        logger.info(f"Login successful: {user.id} - {user.email}")

        # Update last login (optional)
        await self.user_repository.update_last_login(user.id)
        await self.session.commit()

        # Generate tokens
        tokens = self._generate_tokens(user)

        return user, tokens

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New token pair
            
        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        verify_token_type(payload, "refresh")

        # Get user from token
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(message="Invalid token payload")

        user = await self.user_repository.get_by_id(int(user_id))
        if not user:
            raise UnauthorizedException(message="User not found")

        if not user.is_active:
            raise UnauthorizedException(message="Account disabled")

        # Generate new tokens
        return self._generate_tokens(user)

    async def get_current_user(self, token: str) -> User:
        """
        Get current user from access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Current user
            
        Raises:
            UnauthorizedException: If token is invalid or user not found
        """
        # Decode and validate token
        payload = decode_token(token)
        verify_token_type(payload, "access")

        # Get user from token
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(message="Invalid token payload")

        user = await self.user_repository.get_by_id(int(user_id))
        if not user:
            raise UnauthorizedException(message="User not found")

        if not user.is_active:
            raise UnauthorizedException(message="Account disabled")

        return user

    def _generate_tokens(self, user: User) -> TokenResponse:
        """
        Generate access and refresh tokens for user.
        
        Args:
            user: User instance
            
        Returns:
            Token response with access and refresh tokens
        """
        # Token payload
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }

        # Create tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
