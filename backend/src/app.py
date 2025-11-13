import logging
import os
import time
import uuid
from typing import Any

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from src.config import get_config
from src.config.logging_config import clear_request_context, set_request_context, setup_logging
from src.utils.latency_tracker import LatencyTracker

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
socketio = SocketIO(cors_allowed_origins="*")  # Configure CORS for WebSocket

logger = logging.getLogger("src.app")

def create_app(config_name: str | None = None) -> Flask:
    """Application factory for the VigilantEye backend."""

    app = Flask(__name__)
    config = get_config(config_name)
    app.config.from_object(config)
    override_db_uri = os.getenv("ALEMBIC_SQLALCHEMY_URL")
    if override_db_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = override_db_uri

    setup_logging(config)
    _initialize_extensions(app, config)
    _register_error_handlers(app)
    _register_middlewares(app, config)

    from src.api.auth import auth_bp
    from src.api.health import health_bp
    from src.api.reports import reports_bp
    from src.api.storage import storage_bp
    from src.api.telegram import telegram_bp
    from src.api.tickets import tickets_bp
    from src.api.videos import videos_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(storage_bp, url_prefix="/api/storage")
    app.register_blueprint(videos_bp, url_prefix="/api/videos")
    app.register_blueprint(tickets_bp, url_prefix="/api/tickets")
    app.register_blueprint(telegram_bp, url_prefix="/api/telegram")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(health_bp)  # No url_prefix - health endpoints at root level

    # Import WebSocket handlers to register them
    import src.utils.websocket_utils  # noqa: F401

    return app


def _initialize_extensions(app: Flask, config: Any) -> None:
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {"origins": config.CORS_ORIGINS},
            r"/health": {"origins": config.CORS_ORIGINS},
            r"/health/ready": {"origins": config.CORS_ORIGINS},
            r"/metrics": {"origins": config.CORS_ORIGINS},
        },
    )
    limiter.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins=config.CORS_ORIGINS,
        async_mode=config.WEBSOCKET_ASYNC_MODE,
        ping_interval=config.WEBSOCKET_PING_INTERVAL,
        ping_timeout=config.WEBSOCKET_PING_TIMEOUT,
    )


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

    @app.errorhandler(429)
    def handle_rate_limit(error: Exception) -> Any:
        logger.warning("Rate limit exceeded", extra={"context": {"error": str(error)}})
        response = jsonify({"error": "Too many requests"})
        retry_after = getattr(error, "retry_after", None)
        if retry_after is not None:
            try:
                response.headers["Retry-After"] = str(int(retry_after))
            except (TypeError, ValueError):
                response.headers["Retry-After"] = str(retry_after)
        return response, 429

    @app.errorhandler(500)
    def handle_internal_error(error: Exception) -> Any:
        logger.exception("Internal server error", extra={"context": {"error": str(error)}})
        return jsonify({"error": "Internal server error"}), 500


def _register_middlewares(app: Flask, config: Any) -> None:
    # Initialize latency tracker (singleton) with configured max samples
    latency_tracker = LatencyTracker(max_samples=config.LATENCY_TRACKER_MAX_SAMPLES)

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
        duration = time.perf_counter() - getattr(g, "start_time", time.perf_counter())
        duration_ms = duration * 1000

        # Track latency for all endpoints (except health/metrics to avoid noise)
        endpoint = request.endpoint or "unknown"
        if endpoint not in ("health.health", "health.health_ready", "health.metrics"):
            latency_tracker.add_latency(endpoint, duration_ms)

        # Skip logging for health/metrics endpoints (too noisy)
        if request.path not in ("/health", "/health/ready", "/metrics"):
            # Extract user_id from JWT if available
            user_id = None
            try:
                from flask_jwt_extended import get_jwt_identity

                jwt_identity = get_jwt_identity()
                if jwt_identity:
                    user_id = str(jwt_identity)
            except Exception:
                pass  # No JWT token or invalid token

            logger.info(
                "Request completed",
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                        "user_id": user_id,
                        "ip": request.remote_addr,
                        "user_agent": request.headers.get("User-Agent", ""),
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
    socketio.run(application, host="0.0.0.0", port=5000, debug=application.config.get("DEBUG", False))

