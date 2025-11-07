"""Backend application factory for VigilentEye."""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

from .config import Config

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application instance.

    TODO: Full implementation in Integration Service phase.
    """

    app = Flask(__name__)
    app.config.from_object(Config)
    Config.validate()

    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=Config.CORS_SUPPORTS_CREDENTIALS)

    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins=Config.CORS_ORIGINS)
    limiter.init_app(app)

    return app

