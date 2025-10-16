from .model_interface import BaseModel
from app.logger import logger

class SpeechToText(BaseModel):
    def analyze(self, image_path: str | None = None, audio_path: str | None = None):
        logger.info(f"SpeechToText analyzing {audio_path}")
        # stub: integrate Whisper or VOSK
        return {"transcript": "", "language": "en", "confidence": 0.0}
