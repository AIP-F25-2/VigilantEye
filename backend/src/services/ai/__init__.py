"""AI Services module for VigilantEye."""

# Export main AI service classes and functions
from .ai_orchestrator import AIOrchestrator
from .audio_services import AudioClassifier, process_audio_parallel
from .face_recognition_service import FaceRecognitionService, analyze_faces_in_image
from .image_analysis_service import ObjectDetectionService, analyze_image_complete
from .threat_detection_service import ThreatDetectionService, detect_threats_in_frame
from .clothing_recognition_service import ClothingRecognitionService, analyze_persons_in_image
from .model_cache_manager import ModelCacheManager, get_model_cache_manager, get_cached_model
from .threadpool_manager import AIThreadPoolManager, get_ai_threadpool, shutdown_ai_threadpool
from .vector_db_manager import VectorDBManager, find_or_create_face_id
from .person_vector_db_manager import PersonVectorDBManager

__all__ = [
    # Orchestrator
    "AIOrchestrator",
    
    # Audio Services
    "AudioClassifier",
    "process_audio_parallel",
    
    # Face Recognition
    "FaceRecognitionService",
    "analyze_faces_in_image",
    
    # Image Analysis
    "ObjectDetectionService",
    "analyze_image_complete",
    
    # Threat Detection
    "ThreatDetectionService",
    "detect_threats_in_frame",
    
    # Clothing Recognition
    "ClothingRecognitionService",
    "analyze_persons_in_image",
    
    # Model Cache
    "ModelCacheManager",
    "get_model_cache_manager",
    "get_cached_model",
    
    # Thread Pool
    "AIThreadPoolManager",
    "get_ai_threadpool",
    "shutdown_ai_threadpool",
    
    # Vector DB
    "VectorDBManager",
    "find_or_create_face_id",
    "PersonVectorDBManager",
]
