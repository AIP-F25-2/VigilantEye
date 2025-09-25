import os
from pathlib import Path
from dotenv import load_dotenv
import json

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # optional .env

class Config:
    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")  # e.g. mysql+pymysql://user:pass@host/db
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-me")  # simple secret in webhook path or header

    # Channels/config file
    # Alternate channels can be in JSON file or environment variable
    ALT_CHANNELS_FILE = os.getenv("ALT_CHANNELS_FILE", str(BASE_DIR / "alternate_channels.json"))

    # Scheduler settings
    ESCALATE_AFTER_SECONDS = int(os.getenv("ESCALATE_AFTER_SECONDS", 15*60))   # 15 minutes default
    CLOSE_AFTER_SECONDS = int(os.getenv("CLOSE_AFTER_SECONDS", 60*60))         # 1 hour default

    # APScheduler
    SCHEDULER_API_ENABLED = True

    # Misc
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

def load_alternate_channels():
    try:
        with open(Config.ALT_CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
