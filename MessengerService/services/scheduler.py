from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime, timedelta
from services.db import SessionLocal
from services.models import OutboundMessage, MessageStatus
from services.telegram_client import send_text, send_photo, build_ack_button
from config import Config, load_alternate_channels
import logging

logger = logging.getLogger(__name__)
sched = BackgroundScheduler()
ALT = load_alternate_channels()

def schedule_post_actions(message_id: str, created_at: datetime):
    """
    Schedule escalate and close jobs.
    """
    # Escalate job: created_at + ESCALATE_AFTER_SECONDS
    esc_time = created_at + timedelta(seconds=Config.ESCALATE_AFTER_SECONDS)
    close_time = created_at + timedelta(seconds=Config.CLOSE_AFTER_SECONDS)

    sched.add_job(func=escalate_job,
                  trigger="date",
                  run_date=esc_time,
                  args=[message_id],
                  id=f"escalate_{message_id}")

    sched.add_job(func=close_job,
                  trigger="date",
                  run_date=close_time,
                  args=[message_id],
                  id=f"close_{message_id}")

def escalate_job(message_id: str):
    db = SessionLocal()
    try:
        msg = db.get(OutboundMessage, message_id)
        if not msg:
            logger.warning("Escalate: message not found %s", message_id)
            return
        if msg.status in (MessageStatus.acknowledged, MessageStatus.closed, MessageStatus.escalated):
            logger.info("Escalate: skipping as status=%s for %s", msg.status, message_id)
            return

        # send to alternate channel
        alt_channel = ALT.get("escalation_channel")
        if not alt_channel:
            logger.error("Escalation channel not configured.")
            return

        inline = build_ack_button(msg.id)
        if msg.source_type == "text":
            r = send_text(alt_channel, msg.content, inline_button=inline)
        else:
            r = send_photo(alt_channel, msg.content, caption=msg.content if len(msg.content) < 1024 else None, inline_button=inline)

        # update DB
        msg.status = MessageStatus.escalated
        msg.meta = (msg.meta or {})
        msg.meta["escalation_send_response"] = r
        msg.telegram_chat_id = alt_channel  # now we also update which chat it was last sent to
        msg.telegram_message_id = r["result"]["message_id"]
        db.add(msg)
        db.commit()
        logger.info("Escalated message %s to %s", message_id, alt_channel)
    except Exception:
        db.rollback()
        logger.exception("Error during escalate_job")
    finally:
        db.close()

def close_job(message_id: str):
    db = SessionLocal()
    try:
        msg = db.get(OutboundMessage, message_id)
        if not msg:
            logger.warning("Close: message not found %s", message_id)
            return
        if msg.status == MessageStatus.closed:
            logger.info("Close: already closed %s", message_id)
            return

        msg.status = MessageStatus.closed
        db.add(msg)
        db.commit()
        logger.info("Closed message %s", message_id)
    except Exception:
        db.rollback()
        logger.exception("Error during close_job")
    finally:
        db.close()

def start_scheduler():
    if not sched.running:
        sched.start()
