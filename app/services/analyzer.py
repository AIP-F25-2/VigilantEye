from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.audio_classifier import AudioClassifier
from app.models.speech_to_text import SpeechToText
from app.models.image_detector import ImageDetector
from app.models.face_detector import FaceDetector
from app.services.llm_service import evaluate_suspicious
from app.logger import logger
from app.config import settings
from app.db.session import SessionLocal
from app.db.models import Artifact, FaceVector, Evidence, Ticket
import numpy as np

executor = ThreadPoolExecutor(max_workers=settings.THREAD_POOL_WORKERS)

def analyze_artifact_pair(image_artifact_id: str | None, audio_artifact_id: str | None):
    """
    Orchestrates model analyses for a single image + audio (either may be None).
    Saves face vectors to DB (if any), and returns analysis results.
    """
    db = SessionLocal()
    try:
        # resolve paths
        image_path = None
        audio_path = None
        if image_artifact_id:
            art = db.query(Artifact).filter(Artifact.id == image_artifact_id).first()
            image_path = art.path if art else None
        if audio_artifact_id:
            art = db.query(Artifact).filter(Artifact.id == audio_artifact_id).first()
            audio_path = art.path if art else None

        logger.info(f"Analyze pair image={image_path} audio={audio_path}")

        models = [AudioClassifier(), SpeechToText(), ImageDetector(), FaceDetector()]
        results = {}
        futures = {executor.submit(m.analyze, image_path, audio_path): m for m in models}

        for fut in as_completed(futures):
            model = futures[fut]
            try:
                res = fut.result()
                results[model.__class__.__name__] = res
                logger.info(f"{model.__class__.__name__} OK")
                # if face detector returned vectors, save them
                if model.__class__.__name__ == "FaceDetector" and res:
                    faces = res.get("faces", [])
                    for f in faces:
                        vec_bytes = f.get("vector")
                        if vec_bytes:
                            fv = FaceVector(person_id=f.get("person_id"), artifact_id=image_artifact_id, vector=vec_bytes)
                            db.add(fv)
                    db.commit()
            except Exception as e:
                logger.exception(f"Model {model.__class__.__name__} failed: {e}")

        # LLM decision (stub)
        try:
            suspicious = evaluate_suspicious(results)
            logger.info(f"LLM/heuristic decision: suspicious={suspicious}")
        except Exception as e:
            logger.exception(f"LLM failed: {e}")
            suspicious = False

        return {"results": results, "suspicious": suspicious}
    finally:
        db.close()
