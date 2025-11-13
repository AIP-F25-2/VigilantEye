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
    CV2_AVAILABLE = True
    FACE_RECOGNITION_AVAILABLE = False
    try:
        import face_recognition
        FACE_RECOGNITION_AVAILABLE = True
    except ImportError:
        face_recognition = None
        logging.info("face_recognition not available (optional - requires dlib)")
    
    try:
        from PIL import Image, ImageEnhance
        PIL_AVAILABLE = True
    except ImportError:
        Image = None
        ImageEnhance = None
        PIL_AVAILABLE = False
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        SKLEARN_AVAILABLE = True
    except ImportError:
        cosine_similarity = None
        SKLEARN_AVAILABLE = False
except ImportError as e:
    logging.warning(f"FaceAI core dependencies not available: {e}")
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    face_recognition = None
    Image = None
    ImageEnhance = None
    cosine_similarity = None
    FACE_RECOGNITION_AVAILABLE = False
    PIL_AVAILABLE = False
    SKLEARN_AVAILABLE = False

# Add FaceAi path to sys.path
faceai_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'FaceAi', 'VigilantEye-18_FaceAi_Riya')
if faceai_path not in sys.path:
    sys.path.append(faceai_path)

# Initialize logger first
logger = logging.getLogger(__name__)

# Import FaceAi modules
DemographicsAnalyzer = None
ImprovedFaceDetector = None
SimpleAmbiguityChecker = None

if CV2_AVAILABLE:
    try:
        # Handle filename with space: "Age_Gender Detection.py"
        import importlib.util
        age_gender_file = os.path.join(faceai_path, 'Age_Gender Detection.py')
        if os.path.exists(age_gender_file):
            spec = importlib.util.spec_from_file_location("age_gender_detection", age_gender_file)
            age_gender_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(age_gender_module)
            DemographicsAnalyzer = getattr(age_gender_module, 'DemographicsAnalyzer', None)
        
        # Import other modules normally
        from ImprovedFaceDetector import ImprovedFaceDetector
        from Ambiguity import SimpleAmbiguityChecker
        logger.info("FaceAi modules loaded successfully")
    except ImportError as e:
        logger.warning(f"FaceAi modules import error: {e}")
        # Try basic imports as fallback
        try:
            sys.path.insert(0, faceai_path)
            from ImprovedFaceDetector import ImprovedFaceDetector
            from Ambiguity import SimpleAmbiguityChecker
        except ImportError:
            logger.warning("FaceAi modules could not be loaded - basic OpenCV will be used")
    except Exception as e:
        logger.warning(f"Error loading FaceAi modules: {e} - basic OpenCV will be used")

# Basic Face Detector using OpenCV (fallback)
class BasicFaceDetector:
    """Basic face detector using OpenCV Haar cascades"""
    
    def __init__(self, cascade_path):
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV not available")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
    
    def detect_faces(self, image_path_or_array):
        """Detect faces in image"""
        # Load image
        if isinstance(image_path_or_array, str):
            image = cv2.imread(image_path_or_array)
            if image is None:
                return []
        else:
            image = image_path_or_array
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # Format results (convert NumPy types to native Python types for JSON serialization)
        results = []
        for (x, y, w, h) in faces:
            # Convert NumPy int32/int64 to Python int
            x, y, w, h = int(x), int(y), int(w), int(h)
            results.append({
                "bounding_box": [int(y), int(x+w), int(y+h), int(x)],  # top, right, bottom, left (as list for JSON)
                "confidence": float(1.0),
                "detection_method": "opencv_haar"
            })
        
        return results

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
            
            # Try to initialize advanced modules
            advanced_detector_loaded = False
            if ImprovedFaceDetector:
                try:
                    self.face_detector = ImprovedFaceDetector(similarity_threshold=0.35)
                    logger.info("Advanced face detector initialized")
                    advanced_detector_loaded = True
                except Exception as e:
                    logger.warning(f"Advanced face detector not available: {e}")
            
            # If advanced detector failed, use basic OpenCV detector
            if not advanced_detector_loaded:
                self._init_basic_detector()
            
            try:
                if DemographicsAnalyzer:
                    self.demographics_analyzer = DemographicsAnalyzer(model_dir=self.models_dir)
                    logger.info("Demographics analyzer initialized")
            except Exception as e:
                logger.warning(f"Demographics analyzer not available: {e}")
            
            try:
                if SimpleAmbiguityChecker:
                    self.ambiguity_checker = SimpleAmbiguityChecker(ambiguity_threshold=0.7)
                    logger.info("Ambiguity checker initialized")
            except Exception as e:
                logger.warning(f"Ambiguity checker not available: {e}")
            
            # Service is available if we have at least basic face detection
            if self.face_detector:
                self.initialized = True
                logger.info("FaceAi service initialized successfully")
            else:
                logger.warning("FaceAi service: No face detector available")
                self.initialized = False
            
        except Exception as e:
            logger.error(f"Failed to initialize FaceAi service: {e}")
            # Try basic detector as fallback
            if CV2_AVAILABLE:
                self._init_basic_detector()
                if self.face_detector:
                    self.initialized = True
                    logger.info("FaceAi service initialized with basic detector")
                else:
                    self.initialized = False
            else:
                self.initialized = False
    
    def _init_basic_detector(self):
        """Initialize basic OpenCV face detector as fallback"""
        if not CV2_AVAILABLE:
            logger.warning("Cannot initialize basic detector: OpenCV not available")
            return
        
        try:
            # Use OpenCV's built-in Haar cascade for face detection
            import cv2.data
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            
            # Check if cascade file exists
            if not os.path.exists(cascade_path):
                # Try alternative path
                cascade_path = os.path.join(self.models_dir, 'haarcascade_frontalface_default.xml')
            
            if os.path.exists(cascade_path):
                self.face_detector = BasicFaceDetector(cascade_path)
                logger.info(f"Basic OpenCV face detector initialized using: {cascade_path}")
            else:
                logger.error(f"Could not find Haar cascade file at: {cascade_path}")
                logger.error("Face detection will not be available")
        except Exception as e:
            logger.error(f"Could not initialize basic face detector: {e}", exc_info=True)
    
    def is_available(self):
        """Check if FaceAi service is available (at least basic face detection)"""
        return self.initialized and self.face_detector is not None
    
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
            # Check if detector has process_image method (advanced) or detect_faces (basic)
            if hasattr(self.face_detector, 'process_image'):
                results, annotated_image = self.face_detector.process_image(
                    image_path_or_array, show_result=show_result
                )
            elif hasattr(self.face_detector, 'detect_faces'):
                # Basic detector
                results = self.face_detector.detect_faces(image_path_or_array)
                annotated_image = None
            else:
                return {"error": "Face detector method not found"}
            
            # Helper function to convert NumPy types to native Python types
            def convert_numpy_type(value):
                """Convert NumPy types to native Python types"""
                if CV2_AVAILABLE and np is not None:
                    if hasattr(value, 'item'):  # NumPy scalar
                        return value.item()
                    elif isinstance(value, (np.integer, np.int32, np.int64)):
                        return int(value)
                    elif isinstance(value, (np.floating, np.float32, np.float64)):
                        return float(value)
                return value
            
            if isinstance(results, list):
                formatted_results = []
                for result in results:
                    if isinstance(result, dict):
                        # Convert any NumPy types in the dict to native Python types
                        clean_result = {}
                        for key, value in result.items():
                            if isinstance(value, (list, tuple)):
                                # Convert list/tuple elements
                                clean_result[key] = [convert_numpy_type(v) for v in value]
                            else:
                                clean_result[key] = convert_numpy_type(value)
                        formatted_results.append(clean_result)
                    elif isinstance(result, tuple):
                        # Handle tuple format
                        if len(result) >= 4:
                            x, y, w, h = [convert_numpy_type(v) for v in result[:4]]
                            confidence = convert_numpy_type(result[4]) if len(result) > 4 else 1.0
                            formatted_results.append({
                                "bounding_box": [int(y), int(x+w), int(y+h), int(x)],  # as list for JSON
                                "confidence": float(confidence)
                            })
                results = formatted_results
            
            return {
                "success": True,
                "faces_detected": len(results) if isinstance(results, list) else 0,
                "results": results if isinstance(results, list) else [],
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
        # Helper function to convert NumPy types (defined here for use in this method)
        def convert_numpy_type(value):
            """Convert NumPy types to native Python types"""
            if CV2_AVAILABLE and np is not None:
                if hasattr(value, 'item'):  # NumPy scalar
                    return value.item()
                elif isinstance(value, (np.integer, np.int32, np.int64)):
                    return int(value)
                elif isinstance(value, (np.floating, np.float32, np.float64)):
                    return float(value)
            return value
        
        if not self.demographics_analyzer:
            # Return a helpful error message with available alternatives
            return {
                "error": "Demographics analyzer not available. Advanced FaceAI modules are required for age and gender analysis. Basic face detection is available.",
                "available_features": {
                    "face_detection": self.face_detector is not None,
                    "demographics": False,
                    "ambiguity_check": self.ambiguity_checker is not None
                },
                "suggestion": "To enable demographics analysis, ensure the advanced FaceAI modules (Age_Gender Detection.py) are properly installed."
            }
        
        try:
            results = self.demographics_analyzer.analyze(image_path)
            
            # Format results for API response
            formatted_results = []
            for result in results:
                if isinstance(result, dict):
                    # Convert NumPy types to native Python types
                    clean_result = {
                        "face_box": result.get("face_box"),
                        "gender": result.get("gender"),
                        "gender_score": float(result.get("gender_score", 0.0)) if result.get("gender_score") is not None else None,
                        "age_group": result.get("age_group"),
                        "age_score": float(result.get("age_score", 0.0)) if result.get("age_score") is not None else None,
                        "ethnicity": result.get("ethnicity")
                    }
                    # Convert face_box if it's a list/tuple with NumPy types
                    if isinstance(clean_result["face_box"], (list, tuple)):
                        clean_result["face_box"] = [convert_numpy_type(v) for v in clean_result["face_box"]]
                    formatted_results.append(clean_result)
                elif isinstance(result, tuple) and len(result) >= 5:
                    # Handle tuple format from demographics.py
                    x1, y1, x2, y2, label = result
                    x1, y1, x2, y2 = [convert_numpy_type(v) for v in [x1, y1, x2, y2]]
                    formatted_results.append({
                        "face_box": [int(x1), int(y1), int(x2-x1), int(y2-y1)],
                        "label": str(label) if label else None,
                        "gender": label.split(',')[0] if label and ',' in label else None,
                        "age_group": label.split(',')[1].strip() if label and ',' in label else None
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
            # Return a helpful error message with available alternatives
            return {
                "error": "Ambiguity checker not available. Advanced FaceAI modules are required for face comparison and ambiguity analysis. Basic face detection is available.",
                "available_features": {
                    "face_detection": self.face_detector is not None,
                    "demographics": self.demographics_analyzer is not None,
                    "ambiguity_check": False
                },
                "suggestion": "To enable ambiguity checking, ensure the advanced FaceAI modules (Ambiguity.py) are properly installed."
            }
        
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
