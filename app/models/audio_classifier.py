from .model_interface import BaseModel
from app.logger import logger

class AudioClassifier(BaseModel):
    def analyze(self, image_path: str | None = None, audio_path: str | None = None):
        logger.info(f"AudioClassifier analyzing {audio_path}")
        # stub: implement classifier or call to external model
        # return shape: {"audio_event": "gunshot"|"scream"|"none", "confidence": 0.0}
        return {"audio_event": "none", "confidence": 0.0}
