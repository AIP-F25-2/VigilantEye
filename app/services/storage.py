import os
import uuid
import shutil
from datetime import datetime, timedelta
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Artifact
from app.logger import logger

def save_bytes(data: bytes, subfolder: str, suffix: str) -> str:
    """Save raw bytes to storage path and create Artifact DB record; returns artifact id."""
    db = SessionLocal()
    try:
        art_id = str(uuid.uuid4())
        target_dir = os.path.join(str(settings.STORAGE_PATH), subfolder)
        os.makedirs(target_dir, exist_ok=True)
        filename = f"{art_id}{suffix}"
        path = os.path.join(target_dir, filename)
        with open(path, "wb") as f:
            f.write(data)
        expires_at = datetime.utcnow() + timedelta(seconds=settings.TTL_SECONDS)
        artifact = Artifact(id=art_id, type=subfolder, path=path, expires_at=expires_at)
        db.add(artifact)
        db.commit()
        logger.info(f"Saved artifact {art_id} at {path} (expires {expires_at})")
        return art_id
    except Exception as e:
        logger.exception(f"Failed to save bytes: {e}")
        raise
    finally:
        db.close()

def delete_artifact_by_id(artifact_id: str):
    db = SessionLocal()
    try:
        art = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not art:
            logger.warning(f"Artifact {artifact_id} not found")
            return False
        try:
            if os.path.exists(art.path):
                os.remove(art.path)
        except Exception:
            logger.exception("Error removing file from disk")
        db.delete(art)
        db.commit()
        logger.info(f"Deleted artifact {artifact_id}")
        return True
    except Exception as e:
        logger.exception(f"Error deleting artifact {artifact_id}: {e}")
        raise
    finally:
        db.close()
