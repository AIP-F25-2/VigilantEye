import requests
from config import Config
import logging
from urllib.parse import urljoin

API_BASE = "https://api.telegram.org/bot{token}/".format(token=Config.TELEGRAM_BOT_TOKEN)
logger = logging.getLogger(__name__)

def _post(method, payload=None, files=None):
    url = urljoin(API_BASE, method)
    try:
        resp = requests.post(url, json=payload, files=files, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("Telegram API error: %s", e)
        raise

def send_text(chat_id: str, text: str, inline_button=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",  # optional
        "disable_web_page_preview": True
    }
    if inline_button:
        payload["reply_markup"] = inline_button
    return _post("sendMessage", payload)

def send_photo(chat_id: str, photo_url_or_bytes, caption=None, inline_button=None):
    # If photo_url_or_bytes is a URL, use 'photo' as string. requests will handle posting JSON param
    payload = {
        "chat_id": chat_id,
        "photo": photo_url_or_bytes
    }
    if caption:
        payload["caption"] = caption
    if inline_button:
        payload["reply_markup"] = inline_button
    return _post("sendPhoto", payload)

def build_ack_button(message_internal_id: str):
    # Pressing this will create a callback_query with data 'ack:<id>'
    keyboard = {
        "inline_keyboard": [
            [{"text": "Acknowledge", "callback_data": f"ack:{message_internal_id}"}]
        ]
    }
    return keyboard
