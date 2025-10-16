from .main import main_bp
from .api import api_bp
from .auth_controller import auth_bp
from .video_controller import video_bp
from .recording_controller import recording_bp
from .project_controller import project_bp
from .telegram_controller import bp as telegram_bp
from .webhook_controller import bp as webhook_bp

__all__ = [
    'main_bp', 'api_bp', 'auth_bp', 'video_bp', 
    'recording_bp', 'project_bp', 'telegram_bp', 'webhook_bp'
]