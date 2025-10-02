from flask import Flask
from flask_cors import CORS
from .config import Config, ensure_dirs
from .blueprints import register_blueprints

def create_app() -> Flask:
    ensure_dirs()
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)  # allow all; tighten in prod
    register_blueprints(app)
    return app
