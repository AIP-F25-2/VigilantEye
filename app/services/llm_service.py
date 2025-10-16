from app.logger import logger

def evaluate_suspicious(template_inputs: dict) -> bool:
    """
    Stub for LLM decision. For production, call an LLM with a prompt template.
    Heuristic for now: audio event is gunshot|scream or face count > 0 and object 'weapon' present.
    """
    try:
        audio = template_inputs.get("AudioClassifier", {})
        image = template_inputs.get("ImageDetector", {})
        face = template_inputs.get("FaceDetector", {})
        audio_event = audio.get("audio_event") if audio else None
        face_count = face.get("count", 0) if face else 0
        objects = image.get("objects", []) if image else []
        if audio_event in ("gunshot", "scream"):
            return True
        if "weapon" in [o.get("label") if isinstance(o, dict) else o for o in objects]:
            return True
        if face_count > 3:
            # many people could be suspicious in this heuristic
            return True
        return False
    except Exception as e:
        logger.exception(f"LLM heuristic failed: {e}")
        return False
