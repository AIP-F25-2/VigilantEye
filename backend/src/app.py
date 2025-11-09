import logging
import time
import uuid
from typing import Any

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

from src.config import get_config
from src.config.logging_config import clear_request_context, set_request_context, setup_logging

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

logger = logging.getLogger("src.app")


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for the VigilantEye backend."""

    app = Flask(__name__)
    config = get_config(config_name)
    app.config.from_object(config)

    setup_logging(config)
    _initialize_extensions(app, config)
    _register_error_handlers(app)
    _register_middlewares(app, config)

    # Blueprint registrations will be handled in subsequent phases
    # from src.api.auth import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")

    @app.route("/health", methods=["GET"])
    def health_check() -> Any:
        return jsonify({"status": "ok", "timestamp": time.time()}), 200

    return app


def _initialize_extensions(app: Flask, config: Any) -> None:
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, origins=config.CORS_ORIGINS)
    limiter.init_app(app)
    limiter.limit(config.RATE_LIMIT_LOGIN, methods=["POST"])(
        lambda: None
    )  # Placeholder for login endpoint


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def handle_bad_request(error: Exception) -> Any:
        logger.warning("Bad request encountered", extra={"context": {"error": str(error)}})
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(401)
    def handle_unauthorized(error: Exception) -> Any:
        logger.warning(
            "Unauthorized access blocked", extra={"context": {"error": str(error)}}
        )
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def handle_forbidden(error: Exception) -> Any:
        logger.warning("Forbidden access attempt", extra={"context": {"error": str(error)}})
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def handle_not_found(error: Exception) -> Any:
        logger.info("Resource not found", extra={"context": {"error": str(error)}})
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def handle_internal_error(error: Exception) -> Any:
        logger.exception("Internal server error", extra={"context": {"error": str(error)}})
        return jsonify({"error": "Internal server error"}), 500


def _register_middlewares(app: Flask, config: Any) -> None:
    @app.before_request
    def start_request_timer() -> None:
        g.start_time = time.perf_counter()
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        user_id = getattr(getattr(request, "user", None), "id", None)
        user_role = getattr(getattr(request, "user", None), "role", None)
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            user_role=user_role,
            extra={
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
            },
        )

    @app.after_request
    def log_request_details(response: Any) -> Any:
        duration = time.perf_counter() - g.get("start_time", time.perf_counter())
        logger.info(
            "Request completed",
            extra={
                "context": {
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "content_length": response.content_length,
                }
            },
        )
        clear_request_context()
        return response

    @app.teardown_request
    def teardown_request(exception: Exception | None) -> None:
        if exception:
            logger.exception(
                "Unhandled exception during request",
                extra={"context": {"error": str(exception)}},
            )
        clear_request_context()


if __name__ == "__main__":
    application = create_app()
    application.run(
        host="0.0.0.0",
        port=5000,
        debug=application.config.get("DEBUG", False),
    )

