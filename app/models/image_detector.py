from .model_interface import BaseModel
from app.logger import logger

class ImageDetector(BaseModel):
    def analyze(self, image_path: str | None = None, audio_path: str | None = None):
        logger.info(f"ImageDetector analyzing {image_path}")
        # stub: integrate YOLO/Detectron
        return {"objects": [], "description": "no objects detected"}
