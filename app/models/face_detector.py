from .model_interface import BaseModel
from app.logger import logger
import numpy as np

class FaceDetector(BaseModel):
    def analyze(self, image_path: str | None = None, audio_path: str | None = None):
        logger.info(f"FaceDetector analyzing {image_path}")
        # stub: detect faces and return embeddings as bytes
        # For demo produce 0 or 1 fake face
        fake_vector = np.random.rand(128).astype("float32").tobytes()
        return {
            "faces": [
                {
                    "person_id": f"p_{image_path.split('/')[-1]}",
                    "bbox": [0, 0, 10, 10],
                    "vector": fake_vector  # bytes
                }
            ],
            "count": 1
        }
