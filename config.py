import os
from typing import Dict, Any

class Config:
    """Configuration class for the application"""
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'mysql+pymysql://flaskuser:flaskpass@localhost:3306/flaskapi')
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string')
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8345256867:AAFMasgNavOAstsxPdnOazZfHNRHoNJTbQ0')
    TELEGRAM_WEBHOOK_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', 'supersecret')
    
    # Message Processing Configuration
    ESCALATE_AFTER_SECONDS = int(os.environ.get('ESCALATE_AFTER_SECONDS', '900'))  # 15 minutes
    CLOSE_AFTER_SECONDS = int(os.environ.get('CLOSE_AFTER_SECONDS', '3600'))  # 1 hour
    
    # Alternate channels configuration
    ALT_CHANNELS_FILE = os.environ.get('ALT_CHANNELS_FILE', 'alternate_channels.json')
    
    # Default channels
    DEFAULT_CHANNEL = os.environ.get('DEFAULT_CHANNEL', '')
    ESCALATION_CHANNEL = os.environ.get('ESCALATION_CHANNEL', '')

def load_alternate_channels() -> Dict[str, Any]:
    """Load alternate channel configuration from JSON file or environment"""
    import json
    import os
    
    # Try to load from JSON file first
    if os.path.exists(Config.ALT_CHANNELS_FILE):
        try:
            with open(Config.ALT_CHANNELS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {Config.ALT_CHANNELS_FILE}: {e}")
    
    # Fallback to environment variables
    return {
        "escalation_channel": Config.ESCALATION_CHANNEL,
        "default_channel": Config.DEFAULT_CHANNEL
    }
