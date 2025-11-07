"""Face detection and recognition services."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1

from src.config.ai_config import AIConfig
from src.services.ai.model_cache_manager import get_cached_model
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()

# Try to import deepface (optional, for face attribute analysis)
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except (ImportError, Exception) as e:
    DeepFace = None
    DEEPFACE_AVAILABLE = False
    logger.warning(f"deepface not available: {e}. Face attribute analysis (age, gender, emotion) will be disabled.")


class FaceRecognitionService:
    """Face detection, recognition, and demographics analysis."""

    def __init__(self):
        """Initialize face recognition models."""
        self.device = torch.device(ai_config.ai_device)
        
        # Load cached models or create new ones
        self.mtcnn = get_cached_model('mtcnn', str(self.device))
        self.resnet = get_cached_model('facenet_resnet', str(self.device))
        
        if self.mtcnn is None or self.resnet is None:
            logger.error("Failed to load face recognition models")
            raise RuntimeError("Face recognition models could not be loaded")
        
        logger.info("Face recognition service initialized with cached models")

    def detect_faces(self, image_path: str) -> List[Dict]:
        """
        Detect faces in image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected faces with bounding boxes
        """
        logger.info(f"Detecting faces in: {image_path}")
        
        try:
            # Load image
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            boxes, probs = self.mtcnn.detect(image_rgb)
            
            if boxes is None:
                logger.info("No faces detected")
                return []
            
            faces = []
            for i, (box, prob) in enumerate(zip(boxes, probs)):
                x1, y1, x2, y2 = box.astype(int)
                
                faces.append({
                    'face_index': i,
                    'bounding_box': {
                        'x': int(x1),
                        'y': int(y1),
                        'width': int(x2 - x1),
                        'height': int(y2 - y1)
                    },
                    'confidence': float(prob)
                })
            
            logger.info(f"Detected {len(faces)} faces")
            return faces
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}", exc_info=True)
            return []

    def get_face_embedding(self, image_path: str, face_box: Dict) -> Optional[np.ndarray]:
        """
        Get face embedding vector.
        
        Args:
            image_path: Path to image file
            face_box: Bounding box dictionary
            
        Returns:
            Face embedding vector (512-dim)
        """
        try:
            # Load and crop face
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            x = face_box['x']
            y = face_box['y']
            w = face_box['width']
            h = face_box['height']
            
            face_crop = image_rgb[y:y+h, x:x+w]
            
            # Resize to 160x160
            face_resized = cv2.resize(face_crop, (160, 160))
            face_tensor = torch.from_numpy(face_resized).permute(2, 0, 1).float()
            face_tensor = face_tensor.unsqueeze(0).to(self.device)
            
            # Normalize
            face_tensor = (face_tensor - 127.5) / 128.0
            
            # Get embedding
            with torch.no_grad():
                embedding = self.resnet(face_tensor)
            
            return embedding.cpu().numpy()[0]
            
        except Exception as e:
            logger.error(f"Face embedding failed: {e}")
            return None

    def analyze_face_attributes(self, image_path: str, face_box: Dict) -> Dict:
        """
        Analyze face attributes (age, gender, emotion, etc.).
        
        Args:
            image_path: Path to image file
            face_box: Bounding box dictionary
            
        Returns:
            Dictionary with face attributes
        """
        # Check if deepface is available
        if not DEEPFACE_AVAILABLE or DeepFace is None:
            logger.warning("Face attribute analysis disabled - deepface not available")
            return {
                'estimated_age': None,
                'age_range': None,
                'gender': None,
                'gender_confidence': 0.0,
                'emotion': 'neutral',
                'emotion_confidence': 0.0,
                'ethnicity': None,
                'disabled': True,
                'error': 'deepface not available'
            }
        
        try:
            # Crop face region
            image = cv2.imread(image_path)
            x = face_box['x']
            y = face_box['y']
            w = face_box['width']
            h = face_box['height']
            
            # Add padding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = w + 2 * padding
            h = h + 2 * padding
            
            face_crop = image[y:y+h, x:x+w]
            
            # Save temp crop (use tempfile for Windows compatibility)
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"face_crop_{uuid.uuid4()}.jpg")
            cv2.imwrite(temp_path, face_crop)
            
            # Analyze with DeepFace
            analysis = DeepFace.analyze(
                temp_path,
                actions=['age', 'gender', 'emotion', 'race'],
                enforce_detection=False
            )
            
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
            
            # Extract results (handle list or dict)
            if isinstance(analysis, list):
                analysis = analysis[0]
            
            # Parse results
            attributes = {
                'estimated_age': int(analysis.get('age', 0)),
                'age_range': self._get_age_range(int(analysis.get('age', 0))),
                'gender': analysis.get('dominant_gender', 'unknown'),
                'gender_confidence': float(
                    analysis.get('gender', {}).get(analysis.get('dominant_gender', ''), 0)
                ),
                'emotion': analysis.get('dominant_emotion', 'neutral'),
                'emotion_confidence': float(
                    analysis.get('emotion', {}).get(analysis.get('dominant_emotion', ''), 0)
                ),
                'ethnicity': analysis.get('dominant_race', 'unknown'),
                'all_emotions': analysis.get('emotion', {}),
            }
            
            return attributes
            
        except Exception as e:
            logger.error(f"Face attribute analysis failed: {e}")
            return {
                'estimated_age': None,
                'age_range': None,
                'gender': None,
                'gender_confidence': 0.0,
                'emotion': 'neutral',
                'emotion_confidence': 0.0,
                'ethnicity': None,
                'error': str(e)
            }

    def _get_age_range(self, age: int) -> str:
        """Convert age to range string."""
        if age < 3:
            return "0-2"
        elif age < 13:
            return "3-12"
        elif age < 20:
            return "13-19"
        elif age < 30:
            return "20-29"
        elif age < 40:
            return "30-39"
        elif age < 50:
            return "40-49"
        elif age < 60:
            return "50-59"
        elif age < 70:
            return "60-69"
        else:
            return "70+"

    def process_face(self, image_path: str, face_data: Dict) -> Dict:
        """
        Complete face processing: detection, embedding, and attributes.
        
        Args:
            image_path: Path to image file
            face_data: Face detection data with bounding box
            
        Returns:
            Complete face analysis
        """
        try:
            # Get embedding
            embedding = self.get_face_embedding(
                image_path,
                face_data['bounding_box']
            )
            
            # Get attributes
            attributes = self.analyze_face_attributes(
                image_path,
                face_data['bounding_box']
            )
            
            # Generate face ID
            face_id = f"face_{uuid.uuid4().hex[:12]}"
            
            result = {
                'face_id': face_id,
                'bounding_box': face_data['bounding_box'],
                'confidence': face_data['confidence'],
                'embedding': embedding.tolist() if embedding is not None else None,
                'embedding_dim': len(embedding) if embedding is not None else 0,
                **attributes
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Face processing failed: {e}", exc_info=True)
            return {
                'face_id': None,
                'bounding_box': face_data['bounding_box'],
                'error': str(e)
            }


def analyze_faces_in_image(image_path: str, frame_timestamp_ms: int = 0) -> Dict:
    """
    Analyze all faces in an image.
    
    This function is designed to be called in a thread.
    
    Args:
        image_path: Path to image file
        frame_timestamp_ms: Timestamp of frame in video
        
    Returns:
        Dictionary with all face analyses
    """
    logger.info(f"Analyzing faces in: {image_path}")
    
    try:
        service = FaceRecognitionService()
        
        # Detect faces
        faces = service.detect_faces(image_path)
        
        if not faces:
            return {
                'image_path': image_path,
                'frame_timestamp_ms': frame_timestamp_ms,
                'face_count': 0,
                'faces': [],
                'status': 'completed'
            }
        
        # Process each face
        processed_faces = []
        for face in faces:
            processed = service.process_face(image_path, face)
            processed['frame_timestamp_ms'] = frame_timestamp_ms
            processed_faces.append(processed)
        
        result = {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'face_count': len(processed_faces),
            'faces': processed_faces,
            'status': 'completed'
        }
        
        logger.info(
            f"Face analysis completed: {len(processed_faces)} faces processed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Face analysis failed: {e}", exc_info=True)
        return {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'face_count': 0,
            'faces': [],
            'status': 'failed',
            'error': str(e)
        }
