from app.db.session import SessionLocal
from app.db.models import Ticket, Evidence, Artifact
from app.notifications.telegram import TelegramNotifier
from app.logger import logger
from datetime import datetime
import json

notifier = TelegramNotifier()

def create_ticket(artifact_ids: list[str], llm_decision: str) -> Ticket:
    db = SessionLocal()
    try:
        t = Ticket(status="open", evidence=artifact_ids, llm_decision=llm_decision)
        db.add(t)
        db.commit()
        db.refresh(t)
        logger.info(f"Created ticket {t.id} with evidence {artifact_ids}")

        # prepare first attachment (image) if present
        attachments = []
        for aid in artifact_ids:
            art = db.query(Artifact).filter(Artifact.id == aid).first()
            if art and art.type == "images":
                try:
                    with open(art.path, "rb") as f:
                        attachments.append(("image.jpg", f.read()))
                        break
                except Exception:
                    logger.exception("Failed to read attachment file")

        try:
            notifier.send_alert(f"Suspicious event: ticket {t.id}\nDecision: {llm_decision}", attachments=attachments, ticket_id=t.id)
        except Exception:
            logger.exception("Failed to send Telegram alert")

        return t
    finally:
        db.close()

def acknowledge_ticket(ticket_id: int):
    db = SessionLocal()
    try:
        t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not t:
            logger.warning(f"Ticket {ticket_id} not found for acknowledge")
            return None
        t.status = "acknowledged"
        t.closed_at = datetime.utcnow()
        db.add(t)
        db.commit()
        logger.info(f"Ticket {ticket_id} acknowledged")
        return t
    finally:
        db.close()
