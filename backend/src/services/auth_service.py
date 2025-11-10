import logging
import re
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

import redis
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from sqlalchemy.exc import IntegrityError

from src.app import db
from src.config.constants import UserRole
from src.config.settings import get_config
from src.models.audit_log import AuditLog
from src.models.session import Session
from src.models.user import User
from src.utils.db_utils import retry_on_db_error

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class ValidationError(Exception):
    """Raised when input validation fails."""


class AuthorizationError(Exception):
    """Raised when authorization fails."""


class AuthService:
    """Service layer responsible for authentication workflows."""

    def __init__(self) -> None:
        self.config = get_config()
        try:
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=True,
            )
        except redis.RedisError as exc:
            logger.warning("Redis connection failed: %s", exc)
            self.redis_client = None

    @retry_on_db_error()
    def signup(
        self,
        username: str,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        role: str = UserRole.STAFF,
    ) -> Tuple[Optional[User], Optional[Exception]]:
        try:
            self._validate_signup_input(username, email, password, role)

            if User.query.filter_by(username=username).first():
                raise ValidationError("Username already exists")

            if User.query.filter_by(email=email).first():
                raise ValidationError("Email already exists")

            user = User(
                username=username,
                email=email,
                role=self._normalize_role(role),
                is_active=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            self._create_audit_log(
                user_id=user.id,
                action="user_signup",
                resource_type="user",
                resource_id=user.id,
                details={"username": username, "email": email, "role": user.role},
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return user, None
        except ValidationError as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=None,
                action="user_signup",
                resource_type="user",
                resource_id=None,
                details={"username": username, "email": email, "role": role},
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc
        except IntegrityError as exc:
            db.session.rollback()
            logger.error("Signup failed due to integrity error: %s", exc, exc_info=True)
            self._create_audit_log(
                user_id=None,
                action="user_signup",
                resource_type="user",
                resource_id=None,
                details={"username": username, "email": email, "role": role},
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message="Duplicate username or email",
            )
            return None, ValidationError("Username or email already exists")
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error during signup: %s", exc)
            self._create_audit_log(
                user_id=None,
                action="user_signup",
                resource_type="user",
                resource_id=None,
                details={"username": username, "email": email, "role": role},
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc

    @retry_on_db_error()
    def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[User], Optional[Exception]]:
        try:
            user = (
                User.query.filter_by(
                    username=username,
                    is_active=True,
                    is_deleted=False,
                )
                .first()
            )
            if not user:
                raise AuthenticationError("Invalid username or password")

            if not user.check_password(password):
                raise AuthenticationError("Invalid username or password")

            access_token = create_access_token(identity=user)
            refresh_token = create_refresh_token(identity=user)

            now = datetime.utcnow()
            access_expires_at = now + timedelta(seconds=self.config.JWT_ACCESS_TOKEN_EXPIRES)
            refresh_expires_at = now + timedelta(
                seconds=self.config.JWT_REFRESH_TOKEN_EXPIRES
            )

            session = Session(
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
            )
            db.session.add(session)
            user.update_last_login()
            db.session.commit()

            self._cache_token(
                key=f"access_token:{access_token}",
                value=user.id,
                ttl=self.config.JWT_ACCESS_TOKEN_EXPIRES,
            )
            self._cache_token(
                key=f"refresh_token:{refresh_token}",
                value=user.id,
                ttl=self.config.JWT_REFRESH_TOKEN_EXPIRES,
            )

            self._create_audit_log(
                user_id=user.id,
                action="login",
                resource_type="session",
                resource_id=session.id,
                details={
                    "username": username,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return access_token, refresh_token, user, None
        except (AuthenticationError, AuthorizationError) as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=None,
                action="login_failed",
                resource_type="user",
                resource_id=None,
                details={
                    "username": username,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, None, None, exc
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error during login: %s", exc)
            self._create_audit_log(
                user_id=None,
                action="login_error",
                resource_type="user",
                resource_id=None,
                details={
                    "username": username,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, None, None, exc

    @retry_on_db_error()
    def refresh_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[User], Optional[Exception]]:
        try:
            cache_key = f"refresh_token:{refresh_token}"
            token_in_cache = self._token_exists_in_cache(cache_key)

            decoded = decode_token(refresh_token)
            user_id = decoded.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid refresh token payload")

            session = (
                Session.query.filter_by(
                    refresh_token=refresh_token,
                    is_active=True,
                )
                .first()
            )
            if not token_in_cache and not session:
                raise AuthenticationError("Invalid or expired refresh token")

            if not session:
                raise AuthenticationError("Session not found for refresh token")

            if session.is_refresh_expired():
                raise AuthenticationError("Refresh token has expired")

            user = User.query.get(user_id)
            if not user:
                raise AuthenticationError("User not found for refresh token")

            old_access_token = session.access_token

            new_access_token = create_access_token(identity=user)
            new_refresh_token = create_refresh_token(identity=user)

            session.revoke()
            new_session = Session(
                user_id=user.id,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_at=datetime.utcnow()
                + timedelta(seconds=self.config.JWT_ACCESS_TOKEN_EXPIRES),
                refresh_expires_at=datetime.utcnow()
                + timedelta(seconds=self.config.JWT_REFRESH_TOKEN_EXPIRES),
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
            )
            db.session.add(new_session)
            db.session.commit()

            self._delete_cached_tokens(old_access_token, refresh_token)
            self._add_revoked_token_marker(old_access_token)
            self._cache_token(
                key=f"access_token:{new_access_token}",
                value=user.id,
                ttl=self.config.JWT_ACCESS_TOKEN_EXPIRES,
            )
            self._cache_token(
                key=f"refresh_token:{new_refresh_token}",
                value=user.id,
                ttl=self.config.JWT_REFRESH_TOKEN_EXPIRES,
            )

            self._create_audit_log(
                user_id=user.id,
                action="token_refresh",
                resource_type="session",
                resource_id=new_session.id,
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return new_access_token, new_refresh_token, user, None
        except AuthenticationError as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=None,
                action="token_refresh_failed",
                resource_type="session",
                resource_id=None,
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, None, None, exc
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error refreshing token: %s", exc)
            self._create_audit_log(
                user_id=None,
                action="token_refresh_error",
                resource_type="session",
                resource_id=None,
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, None, None, exc

    @retry_on_db_error()
    def logout(
        self,
        access_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[Exception]]:
        try:
            session = (
                Session.query.filter_by(
                    access_token=access_token,
                    is_active=True,
                )
                .first()
            )
            if not session:
                raise AuthenticationError("Active session not found for access token")

            session.revoke()
            db.session.commit()

            self._delete_cached_tokens(access_token, session.refresh_token)
            self._add_revoked_token_marker(access_token)

            self._create_audit_log(
                user_id=session.user_id,
                action="logout",
                resource_type="session",
                resource_id=session.id,
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return True, None
        except AuthenticationError as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=None,
                action="logout_failed",
                resource_type="session",
                resource_id=None,
                details={
                    "access_token": "<redacted>",
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return False, exc
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error during logout: %s", exc)
            self._create_audit_log(
                user_id=None,
                action="logout_error",
                resource_type="session",
                resource_id=None,
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return False, exc

    def validate_token(self, access_token: str) -> Optional[str]:
        if self._token_exists_in_cache(f"access_token:{access_token}"):
            try:
                decoded = decode_token(access_token)
                return decoded.get("sub")
            except Exception as exc:
                logger.warning("Failed to decode cached token: %s", exc)
                return None

        session = (
            Session.query.filter_by(
                access_token=access_token,
                is_active=True,
            )
            .first()
        )
        if not session or session.is_expired():
            return None
        return session.user_id

    @retry_on_db_error()
    def promote_user(
        self,
        user_id: str,
        promoted_by_user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[Exception]]:
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValidationError("User not found")

            if user.role == UserRole.ADMIN:
                raise ValidationError("User is already an admin")

            old_role = user.role
            user.role = UserRole.ADMIN
            db.session.commit()

            self._create_audit_log(
                user_id=promoted_by_user_id,
                action="user_promoted",
                resource_type="user",
                resource_id=user_id,
                details={
                    "old_role": old_role,
                    "new_role": user.role,
                    "promoted_by": promoted_by_user_id,
                },
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return user, None
        except ValidationError as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=promoted_by_user_id,
                action="user_promote_failed",
                resource_type="user",
                resource_id=user_id,
                details={
                    "promoted_by": promoted_by_user_id,
                },
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error promoting user: %s", exc)
            self._create_audit_log(
                user_id=promoted_by_user_id,
                action="user_promote_error",
                resource_type="user",
                resource_id=user_id,
                details={
                    "promoted_by": promoted_by_user_id,
                },
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc

    @retry_on_db_error()
    def demote_user(
        self,
        user_id: str,
        demoted_by_user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[Exception]]:
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValidationError("User not found")

            if user.role == UserRole.STAFF:
                raise ValidationError("User is already staff")

            old_role = user.role
            user.role = UserRole.STAFF
            db.session.commit()

            self._create_audit_log(
                user_id=demoted_by_user_id,
                action="user_demoted",
                resource_type="user",
                resource_id=user_id,
                details={
                    "old_role": old_role,
                    "new_role": user.role,
                    "demoted_by": demoted_by_user_id,
                },
                status="success",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return user, None
        except ValidationError as exc:
            db.session.rollback()
            self._create_audit_log(
                user_id=demoted_by_user_id,
                action="user_demote_failed",
                resource_type="user",
                resource_id=user_id,
                details={
                    "demoted_by": demoted_by_user_id,
                },
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unexpected error demoting user: %s", exc)
            self._create_audit_log(
                user_id=demoted_by_user_id,
                action="user_demote_error",
                resource_type="user",
                resource_id=user_id,
                details={
                    "demoted_by": demoted_by_user_id,
                },
                status="error",
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(exc),
            )
            return None, exc

    def _validate_signup_input(
        self,
        username: str,
        email: str,
        password: str,
        role: str,
    ) -> None:
        if not username or not email or not password:
            raise ValidationError("Username, email, and password are required")

        email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        if password.lower() == password or password.upper() == password:
            raise ValidationError("Password must contain both uppercase and lowercase characters")

        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one digit")

        self._normalize_role(role)

    def _normalize_role(self, role: str) -> str:
        if role not in (UserRole.STAFF, UserRole.ADMIN):
            raise ValidationError("Invalid role specified")
        return role

    def _cache_token(self, key: str, value: str, ttl: int) -> None:
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, value)
            except redis.RedisError as exc:
                logger.warning("Failed to cache token in Redis: %s", exc)

    def _token_exists_in_cache(self, key: str) -> bool:
        if not self.redis_client:
            return False
        try:
            return self.redis_client.exists(key) == 1
        except redis.RedisError as exc:
            logger.warning("Failed to check token in Redis: %s", exc)
            return False

    def _delete_cached_tokens(self, access_token: str, refresh_token: str) -> None:
        if not self.redis_client:
            return
        try:
            self.redis_client.delete(
                f"access_token:{access_token}",
                f"refresh_token:{refresh_token}",
            )
        except redis.RedisError as exc:
            logger.warning("Failed to delete cached tokens from Redis: %s", exc)

    def _add_revoked_token_marker(self, access_token: str) -> None:
        if not self.redis_client:
            return
        try:
            decoded = decode_token(access_token)
            jti = decoded.get("jti")
            if jti:
                self.redis_client.setex(
                    f"revoked_token:{jti}",
                    self.config.JWT_ACCESS_TOKEN_EXPIRES,
                    "1",
                )
        except Exception as exc:
            logger.warning("Failed to mark token as revoked: %s", exc)

    def _create_audit_log(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        details: Optional[dict[str, Any]],
        status: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        error_message: Optional[str] = None,
    ) -> None:
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=error_message,
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.warning("Failed to create audit log: %s", exc)

