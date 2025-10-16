import requests
import json
from app.config import settings
from app.logger import logger

TELEGRAM_API = "https://api.telegram.org"

class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def send_alert(self, text: str, attachments: list[tuple[str, bytes]] = None, ticket_id: int | None = None):
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured; skipping send_alert")
            return None
        try:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Acknowledge", "callback_data": f"ack:{ticket_id}"}]
                ]
            }
            caption = text
            url = f"{TELEGRAM_API}/bot{self.bot_token}/sendPhoto"
            data = {"chat_id": self.chat_id, "caption": caption, "reply_markup": json.dumps(keyboard)}
            files = {}
            if attachments and len(attachments) > 0:
                # attachments is list of (filename, bytes)
                files["photo"] = (attachments[0][0], attachments[0][1])
            else:
                # If no photo, send message instead
                url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
                data = {"chat_id": self.chat_id, "text": text}
            resp = requests.post(url, data=data, files=files if files else None, timeout=10)
            resp.raise_for_status()
            logger.info(f"Telegram alert sent for ticket {ticket_id}")
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to send Telegram alert: {e}")
            return None
