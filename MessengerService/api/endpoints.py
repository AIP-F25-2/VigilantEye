from flask import Blueprint, request, jsonify
from services.db import SessionLocal
from services.models import OutboundMessage, MessageStatus
from services.telegram_client import send_text, send_photo, build_ack_button
from services.scheduler import schedule_post_actions
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")

@bp.route("/ingest", methods=["POST"])
def ingest():
    """
    POST JSON:
    {
      "type": "text" | "image",
      "content": "text body" or "https://...jpg",
      "channel_id": "-10012345678"
    }
    """
    data = request.get_json(force=True)
    typ = data.get("type")
    content = data.get("content")
    channel = data.get("channel_id")
    if typ not in ("text", "image") or not content or not channel:
        return jsonify({"error": "invalid payload"}), 400

    db = SessionLocal()
    try:
        msg = OutboundMessage(
            source_type=typ,
            content=content,
            source_channel=channel,
            status=MessageStatus.initiated,
            meta={"raw_input": data}
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Build inline acknowledge button
        inline = build_ack_button(msg.id)

        # Send message to the provided channel immediately
        if typ == "text":
            resp = send_text(channel, content, inline_button=inline)
        else:
            resp = send_photo(channel, content, caption=None, inline_button=inline)

        # Update DB with sent status and telegram ids
        msg.telegram_chat_id = channel
        msg.telegram_message_id = resp["result"]["message_id"]
        msg.status = MessageStatus.sent
        msg.meta["send_response"] = resp
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Schedule future jobs (escalate and close)
        created_at = msg.created_at or datetime.utcnow()
        schedule_post_actions(msg.id, created_at)
        return jsonify({"id": msg.id, "status": msg.status.value, "telegram": resp["result"]})
    except Exception as e:
        db.rollback()
        logger.exception("ingest error")
        return jsonify({"error": "server error", "details": str(e)}), 500
    finally:
        db.close()
