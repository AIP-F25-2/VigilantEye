from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.outbound_message import OutboundMessage, MessageStatus
import logging

bp = Blueprint("webhooks", __name__, url_prefix="/webhook")

logger = logging.getLogger(__name__)

@bp.route("/telegram/<secret>", methods=["POST"])
def telegram_webhook(secret):
    # verify secret
    if secret != current_app.config["TELEGRAM_WEBHOOK_SECRET"]:
        return "forbidden", 403

    update = request.get_json(force=True)
    # handle callback_query (button press)
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        # expected format: ack:<message_internal_id>
        if data.startswith("ack:"):
            internal_id = data.split(":", 1)[1]
            try:
                msg = OutboundMessage.query.get(internal_id)
                if not msg:
                    logger.warning("ACK for unknown message %s", internal_id)
                else:
                    # Update to acknowledged then to closed (as per user flow: acknowledged -> close)
                    msg.status = MessageStatus.acknowledged
                    msg.meta = (msg.meta or {})
                    msg.meta["acknowledged_by"] = {
                        "from": cb.get("from"),
                        "timestamp": cb.get("date")
                    }
                    msg.save()

                    # immediately also mark as closed (user requested: make acknowledged to close)
                    msg.status = MessageStatus.closed
                    msg.save()
                # We should answer the callback query so UI shows acknowledged
                # reply via Telegram API: answerCallbackQuery
                from app.services.telegram_client import _post
                _post("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Acknowledged. Marked closed."})
            except Exception:
                db.session.rollback()
                logger.exception("Error handling ack callback")
    # return 200 quickly
    return jsonify({"ok": True})
