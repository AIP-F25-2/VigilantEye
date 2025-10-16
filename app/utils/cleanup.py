import time
from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.db.models import Artifact, Ticket
from app.config import settings
from app.logger import logger
import threading

def cleanup_loop():
    while True:
        db = SessionLocal()
        try:
            logger.info("Cleanup worker running")
            now = datetime.utcnow()
            expired = db.query(Artifact).filter(Artifact.expires_at != None, Artifact.expires_at < now).all()
            for a in expired:
                try:
                    logger.info(f"Removing expired artifact {a.id} at {a.path}")
                    import os
                    if os.path.exists(a.path):
                        os.remove(a.path)
                except Exception:
                    logger.exception("Error removing artifact file")
                db.delete(a)

            # auto-close tickets older than AUTO_CLOSE_TICKET_SECONDS
            cutoff = now - timedelta(seconds=settings.AUTO_CLOSE_TICKET_SECONDS)
            old = db.query(Ticket).filter(Ticket.status == "open", Ticket.created_at < cutoff).all()
            for t in old:
                logger.info(f"Auto-closing ticket {t.id}")
                t.status = "closed"
            db.commit()
            logger.info("Cleanup pass complete")
        except Exception as e:
            logger.exception(f"Cleanup pass failed: {e}")
        finally:
            db.close()
            time.sleep(600)

def start_cleanup_thread():
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
