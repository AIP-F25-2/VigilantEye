import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.app import limiter
from src.config.settings import get_config
from src.services.auth_service import (
    AuthService,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
)
from src.utils.auth_middleware import (
    admin_only,
    get_current_user,
    get_request_context,
    require_auth,
)

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService()
config = get_config()
logger = logging.getLogger(__name__)


def _serialize_user(user) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def _is_duplicate_error(error: Exception) -> bool:
    message = str(error).lower()
    return "exists" in message or "duplicate" in message


@auth_bp.route("/signup", methods=["POST"])
def signup():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    context = get_request_context()

    user, error = auth_service.signup(
        username=username,
        email=email,
        password=password,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )
    if error:
        status_code = 400
        if _is_duplicate_error(error):
            status_code = 409
        logger.error(
            "Signup failed",
            extra={
                "context": {
                    "username": username,
                    "email": email,
                    "error": str(error),
                }
            },
        )
        return jsonify({"error": str(error)}), status_code

    return (
        jsonify(
            {
                "message": "User created successfully",
                "user": _serialize_user(user),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(lambda: config.RATE_LIMIT_LOGIN)
def login():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    context = get_request_context()

    (
        access_token,
        refresh_token,
        user,
        error,
    ) = auth_service.login(
        username=username,
        password=password,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )

    if error:
        if isinstance(error, AuthenticationError):
            logger.warning(
                "Login failed",
                extra={
                    "context": {
                        "username": username,
                        "ip_address": context.get("ip_address"),
                        "user_agent": context.get("user_agent"),
                        "error": str(error),
                    }
                },
            )
            return jsonify({"error": "Invalid username or password"}), 401

        logger.exception(
            "Login failed with unexpected error",
            extra={
                "context": {
                    "username": username,
                    "ip_address": context.get("ip_address"),
                    "user_agent": context.get("user_agent"),
                }
            },
        )
        return jsonify({"error": "Internal server error"}), 500

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": _serialize_user(user),
                "expires_in": config.JWT_ACCESS_TOKEN_EXPIRES,
            }
        ),
        200,
    )


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    refresh_token = (data.get("refresh_token") or "").strip()
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    context = get_request_context()
    (
        new_access_token,
        new_refresh_token,
        user,
        error,
    ) = auth_service.refresh_token(
        refresh_token=refresh_token,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )

    if error:
        logger.error(
            "Token refresh failed",
            extra={
                "context": {
                    "ip_address": context.get("ip_address"),
                    "user_agent": context.get("user_agent"),
                    "error": str(error),
                }
            },
        )
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    return (
        jsonify(
            {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_in": config.JWT_ACCESS_TOKEN_EXPIRES,
            }
        ),
        200,
    )


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    context = get_request_context()
    access_token = getattr(request, "headers", {}).get("Authorization", "")
    token_value = ""
    if access_token.startswith("Bearer "):
        token_value = access_token.replace("Bearer ", "", 1).strip()

    success, error = auth_service.logout(
        access_token=token_value,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )

    if error:
        logger.error(
            "Logout failed",
            extra={
                "context": {
                    "ip_address": context.get("ip_address"),
                    "user_agent": context.get("user_agent"),
                    "error": str(error),
                }
            },
        )
        return jsonify({"error": "Unauthorized"}), 401

    current_user_obj = get_current_user()

    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/promote-user", methods=["POST"])
@admin_only
def promote_user():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    context = get_request_context()
    admin_user = get_current_user()

    user, error = auth_service.promote_user(
        user_id=user_id,
        promoted_by_user_id=admin_user.id,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )

    if error:
        status_code = 500
        if isinstance(error, ValidationError):
            message = str(error).lower()
            if "not found" in message:
                status_code = 404
            elif "already" in message:
                status_code = 400
            else:
                status_code = 400
        elif isinstance(error, AuthorizationError):
            status_code = 403
        logger.error(
            "Promote user failed",
            extra={
                "context": {
                    "requested_user_id": user_id,
                    "admin_id": admin_user.id,
                    "error": str(error),
                }
            },
        )
        return jsonify({"error": str(error)}), status_code

    return (
        jsonify(
            {
                "message": "User promoted to admin",
                "user": _serialize_user(user),
            }
        ),
        200,
    )


@auth_bp.route("/demote-user", methods=["POST"])
@admin_only
def demote_user():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    context = get_request_context()
    admin_user = get_current_user()

    user, error = auth_service.demote_user(
        user_id=user_id,
        demoted_by_user_id=admin_user.id,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
    )

    if error:
        status_code = 500
        if isinstance(error, ValidationError):
            message = str(error).lower()
            if "not found" in message:
                status_code = 404
            elif "already" in message:
                status_code = 400
            else:
                status_code = 400
        elif isinstance(error, AuthorizationError):
            status_code = 403
        logger.error(
            "Demote user failed",
            extra={
                "context": {
                    "requested_user_id": user_id,
                    "admin_id": admin_user.id,
                    "error": str(error),
                }
            },
        )
        return jsonify({"error": str(error)}), status_code

    return (
        jsonify(
            {
                "message": "User demoted to staff",
                "user": _serialize_user(user),
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": _serialize_user(user)}), 200


@auth_bp.route("/users", methods=["GET"])
@admin_only
def list_users():
    """List all users (admin only)."""
    try:
        from src.models.user import User
        
        users = User.query.filter_by(is_deleted=False, is_active=True).all()
        return jsonify({"users": [_serialize_user(user) for user in users]}), 200
    except Exception as exc:
        logger.exception("List users failed", extra={"context": {"error": str(exc)}})
        return jsonify({"error": "Internal server error"}), 500
