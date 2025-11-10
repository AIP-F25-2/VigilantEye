import logging
from functools import wraps
from typing import Any, Callable

import redis
from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from src.app import jwt
from src.config.constants import UserRole
from src.config.settings import get_config
from src.models.user import User

logger = logging.getLogger(__name__)

_config = get_config()
try:
    _redis_client = redis.from_url(_config.REDIS_URL, decode_responses=True)
except redis.RedisError as exc:
    logger.warning("Redis connection failed for auth middleware: %s", exc)
    _redis_client = None


def require_auth(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({"error": "Missing authorization header", "code": "unauthorized"}),
                401,
            )

        token = auth_header.replace("Bearer ", "", 1).strip()
        try:
            verify_jwt_in_request()
        except Exception as exc:
            logger.warning("JWT verification failed: %s", exc)
            return jsonify({"error": "Invalid token", "code": "invalid_token"}), 401

        if _config.ENFORCE_ACCESS_TOKEN_ALLOWLIST and _redis_client:
            try:
                if _redis_client.exists(f"access_token:{token}") != 1:
                    logger.warning("Access token not found in allowlist")
                    return jsonify({"error": "Invalid token", "code": "invalid_token"}), 401
            except redis.RedisError as exc:
                logger.warning("Failed to check access token allowlist: %s", exc)

        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Invalid token identity", "code": "invalid_identity"}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found", "code": "user_not_found"}), 401

        if not user.is_active or getattr(user, "is_deleted", False):
            return jsonify({"error": "User inactive", "code": "user_inactive"}), 403

        g.current_user = user
        g.current_access_token = token
        return func(*args, **kwargs)

    return wrapper


def require_role(*roles: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @require_auth
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            user = getattr(g, "current_user", None)
            if not user:
                return jsonify({"error": "Unauthorized", "code": "unauthorized"}), 401

            if user.role not in roles:
                return jsonify({"error": "Forbidden", "code": "forbidden"}), 403

            return func(*args, **kwargs)

        return wrapper

    return decorator


def admin_only(func: Callable) -> Callable:
    return require_role(UserRole.ADMIN)(func)


def get_current_user() -> User | None:
    return getattr(g, "current_user", None)


def get_request_context() -> dict[str, str | None]:
    ip_address = request.headers.get("X-Forwarded-For", "")
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    else:
        ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")
    return {"ip_address": ip_address, "user_agent": user_agent}


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):  # type: ignore[override]
    jti = jwt_payload.get("jti")
    if not jti or not _redis_client:
        return False
    try:
        return _redis_client.exists(f"revoked_token:{jti}") == 1
    except redis.RedisError as exc:
        logger.warning("Failed to check revoked token status: %s", exc)
        return False


@jwt.user_identity_loader
def user_identity_lookup(user: User) -> str:  # type: ignore[override]
    return getattr(user, "id", str(user))


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):  # type: ignore[override]
    identity = jwt_data.get("sub")
    if not identity:
        return None
    return User.query.get(identity)


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):  # type: ignore[override]
    return (
        jsonify({"error": "Token has expired", "code": "token_expired"}),
        401,
    )


@jwt.invalid_token_loader
def invalid_token_callback(error_string):  # type: ignore[override]
    logger.warning("Invalid token encountered: %s", error_string)
    return (
        jsonify({"error": "Invalid token", "code": "invalid_token"}),
        401,
    )


@jwt.unauthorized_loader
def unauthorized_callback(error_string):  # type: ignore[override]
    logger.warning("Unauthorized access attempt: %s", error_string)
    return (
        jsonify({"error": "Missing authorization header", "code": "unauthorized"}),
        401,
    )


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):  # type: ignore[override]
    return (
        jsonify({"error": "Token has been revoked", "code": "token_revoked"}),
        401,
    )

