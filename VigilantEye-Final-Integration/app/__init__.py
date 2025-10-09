from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://flaskuser:flaskpass@localhost:3306/flaskapi')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024  # 20GB
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # We'll handle expiration in tokens
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    jwt.init_app(app)
    
    # Configure JWT
    from app.utils.auth_utils import is_token_revoked
    jwt.token_in_blocklist_loader(is_token_revoked)
    
    # Register blueprints
    from app.controllers import main_bp, api_bp, auth_bp
    from app.controllers.video_controller import video_bp
    from app.controllers.recording_controller import recording_bp
    from app.controllers.project_controller import project_bp
    from app.controllers.camera_controller import camera_bp
    
    # Register main blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Register new API blueprints
    app.register_blueprint(video_bp, url_prefix='/api/v2')
    app.register_blueprint(recording_bp, url_prefix='/api/v2')
    app.register_blueprint(project_bp, url_prefix='/api/v2')
    app.register_blueprint(camera_bp, url_prefix='/api/v2')
    
    # Note: Server blueprints removed - using new API structure
    
    return app
