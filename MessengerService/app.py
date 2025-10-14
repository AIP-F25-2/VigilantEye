from flask import Flask
from config import Config
from api.endpoints import bp as api_bp
from webhooks.telegram_webhook import bp as wh_bp
from api.health import bp as h_bp
from services.db import Base, engine
from services.scheduler import start_scheduler
import logging
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(wh_bp)
    app.register_blueprint(h_bp)

    # Create DB tables if not present (for simple demo). Use migrations for prod.
    Base.metadata.create_all(bind=engine)

    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    # Start scheduler once app is up
    start_scheduler()
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))
