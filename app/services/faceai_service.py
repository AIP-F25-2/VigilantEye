"""
FaceAi Integration Service for VIGILANTEye
Integrates face detection, demographics analysis, and ambiguity detection
"""

import os
import sys
from datetime import datetime
import logging

# Try to import optional dependencies
try:
    import cv2
    import numpy as np
    import face_recognition
    from PIL import Image, ImageEnhance
    from sklearn.metrics.pairwise import cosine_similarity
    CV2_AVAILABLE = True
except ImportError as e:
    logging.warning(f"FaceAI dependencies not available: {e}")
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    face_recognition = None
    Image = None
    ImageEnhance = None
    cosine_similarity = None

# Add FaceAi path to sys.path
faceai_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'FaceAi', 'VigilantEye-18_FaceAi_Riya')
if faceai_path not in sys.path:
    sys.path.append(faceai_path)

# Import FaceAi modules
try:
    if CV2_AVAILABLE:
        from Age_Gender_Detection import DemographicsAnalyzer
        from ImprovedFaceDetector import ImprovedFaceDetector
        from Ambiguity import SimpleAmbiguityChecker
    else:
        DemographicsAnalyzer = None
        ImprovedFaceDetector = None
        SimpleAmbiguityChecker = None
except ImportError as e:
    logging.warning(f"FaceAi modules not available: {e}")
    DemographicsAnalyzer = None
    ImprovedFaceDetector = None
    SimpleAmbiguityChecker = None

logger = logging.getLogger(__name__)

class FaceAiService:
    """Main service class for FaceAi integration"""
    
    def __init__(self, models_dir=None):
        self.models_dir = models_dir or os.path.join(faceai_path, 'models')
        self.face_detector = None
        self.demographics_analyzer = None
        self.ambiguity_checker = None
        self.initialized = False
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize FaceAi components"""
        try:
            if not CV2_AVAILABLE:
                logger.warning("FaceAI dependencies not available. FaceAI features will be disabled.")
                self.initialized = False
                return
            
            if ImprovedFaceDetector:
                self.face_detector = ImprovedFaceDetector(similarity_threshold=0.35)
                logger.info("Face detector initialized")
            
            if DemographicsAnalyzer:
                self.demographics_analyzer = DemographicsAnalyzer(model_dir=self.models_dir)
                logger.info("Demographics analyzer initialized")
            
            if SimpleAmbiguityChecker:
                self.ambiguity_checker = SimpleAmbiguityChecker(ambiguity_threshold=0.7)
                logger.info("Ambiguity checker initialized")
            
            self.initialized = True
            logger.info("FaceAi service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FaceAi service: {e}")
            self.initialized = False
    
    def is_available(self):
        """Check if FaceAi service is available"""
        return self.initialized and all([
            self.face_detector,
            self.demographics_analyzer,
            self.ambiguity_checker
        ])
    
    def detect_faces(self, image_path_or_array, show_result=False):
        """
        Detect and recognize faces in an image
        
        Args:
            image_path_or_array: Path to image file or numpy array
            show_result: Whether to display results
            
        Returns:
            dict: Detection results with face information
        """
        if not self.face_detector:
            return {"error": "Face detector not available"}
        
        try:
            results, annotated_image = self.face_detector.process_image(
                image_path_or_array, show_result=show_result
            )
            
            return {
                "success": True,
                "faces_detected": len(results),
                "results": results,
                "annotated_image": annotated_image
            }
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return {"error": str(e)}
    
    def analyze_demographics(self, image_path):
        """
        Analyze age and gender demographics
        
        Args:
            image_path: Path to image file
            
        Returns:
            dict: Demographics analysis results
        """
        if not self.demographics_analyzer:
            return {"error": "Demographics analyzer not available"}
        
        try:
            results = self.demographics_analyzer.analyze(image_path)
            
            # Format results for API response
            formatted_results = []
            for result in results:
                if isinstance(result, dict):
                    formatted_results.append({
                        "face_box": result.get("face_box"),
                        "gender": result.get("gender"),
                        "gender_score": result.get("gender_score"),
                        "age_group": result.get("age_group"),
                        "age_score": result.get("age_score"),
                        "ethnicity": result.get("ethnicity")
                    })
                elif isinstance(result, tuple) and len(result) >= 5:
                    # Handle tuple format from demographics.py
                    x1, y1, x2, y2, label = result
                    formatted_results.append({
                        "face_box": (x1, y1, x2-x1, y2-y1),
                        "label": label,
                        "gender": label.split(',')[0] if ',' in label else None,
                        "age_group": label.split(',')[1].strip() if ',' in label else None
                    })
            
            return {
                "success": True,
                "faces_analyzed": len(formatted_results),
                "results": formatted_results
            }
            
        except Exception as e:
            logger.error(f"Demographics analysis error: {e}")
            return {"error": str(e)}
    
    def check_ambiguity(self, image1_path_or_array, image2_path_or_array, show_result=False):
        """
        Check if two images show the same person (ambiguity detection)
        
        Args:
            image1_path_or_array: First image (path or array)
            image2_path_or_array: Second image (path or array)
            show_result: Whether to display results
            
        Returns:
            dict: Ambiguity analysis results
        """
        if not self.ambiguity_checker:
            return {"error": "Ambiguity checker not available"}
        
        try:
            is_ambiguous, score, details = self.ambiguity_checker.check_ambiguity(
                image1_path_or_array, image2_path_or_array, show_result=show_result
            )
            
            return {
                "success": True,
                "ambiguous": bool(is_ambiguous),
                "score": float(score),
                "similarities": {k: float(v) for k, v in details.get('similarities', {}).items()},
                "reasons": details.get('reasons', []),
                "weights": details.get('weights', {})
            }
            
        except Exception as e:
            logger.error(f"Ambiguity check error: {e}")
            return {"error": str(e)}
    
    def process_video_frame(self, frame, frame_number=None):
        """
        Process a single video frame for face detection and analysis
        
        Args:
            frame: OpenCV frame (numpy array)
            frame_number: Optional frame number for logging
            
        Returns:
            dict: Frame analysis results
        """
        if not self.face_detector:
            return {"error": "Face detector not available"}
        
        try:
            # Detect faces in frame
            face_results = self.detect_faces(frame, show_result=False)
            
            if face_results.get("error"):
                return face_results
            
            # Add frame metadata
            face_results["frame_number"] = frame_number
            face_results["timestamp"] = datetime.utcnow().isoformat()
            
            return face_results
            
        except Exception as e:
            logger.error(f"Video frame processing error: {e}")
            return {"error": str(e)}
    
    def get_service_status(self):
        """Get FaceAi service status and capabilities"""
        return {
            "initialized": self.initialized,
            "face_detector": self.face_detector is not None,
            "demographics_analyzer": self.demographics_analyzer is not None,
            "ambiguity_checker": self.ambiguity_checker is not None,
            "models_dir": self.models_dir,
            "available": self.is_available()
        }

# Global service instance
faceai_service = FaceAiService()

def get_faceai_service():
    """Get the global FaceAi service instance"""
    return faceai_service
