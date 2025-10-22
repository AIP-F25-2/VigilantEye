"""AI Model Cache Manager - Download and cache AI models for reuse."""

import json
import os
import pickle
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
import requests
from urllib.parse import urlparse
import torch
import torchvision.models as models
from facenet_pytorch import MTCNN, InceptionResnetV1
import cv2
import numpy as np

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class ModelCacheManager:
    """Manages AI model downloads, caching, and reuse."""

    def __init__(self):
        """Initialize model cache manager."""
        self.cache_dir = Path(ai_config.model_cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Model registry with download info
        self.model_registry = {
            # Face Recognition Models
            'mtcnn': {
                'type': 'facenet_pytorch',
                'class': MTCNN,
                'args': {
                    'keep_all': True,
                    'min_face_size': 40,
                    'thresholds': [0.6, 0.7, ai_config.face_detection_confidence]
                },
                'version': '1.0.0',
                'device_dependent': True
            },
            'facenet_resnet': {
                'type': 'facenet_pytorch',
                'class': InceptionResnetV1,
                'args': {'pretrained': 'vggface2'},
                'version': '1.0.0',
                'device_dependent': True
            },
            
            # Computer Vision Models
            'resnet50': {
                'type': 'torchvision',
                'class': models.resnet50,
                'args': {'pretrained': True},
                'version': '1.0.0',
                'device_dependent': True
            },
            'resnet18': {
                'type': 'torchvision',
                'class': models.resnet18,
                'args': {'pretrained': True},
                'version': '1.0.0',
                'device_dependent': True
            },
            'efficientnet_b0': {
                'type': 'torchvision',
                'class': models.efficientnet_b0,
                'args': {'pretrained': True},
                'version': '1.0.0',
                'device_dependent': True
            },
            
            # OpenCV Models
            'opencv_hog': {
                'type': 'opencv',
                'class': 'HOGDescriptor',
                'args': {},
                'version': '1.0.0',
                'device_dependent': False
            },
            'opencv_haar_cascade': {
                'type': 'opencv',
                'class': 'CascadeClassifier',
                'args': {'xml_file': 'haarcascade_frontalface_default.xml'},
                'version': '1.0.0',
                'device_dependent': False
            },
            
            # YOLO Models
            'yolov8n': {
                'type': 'yolo',
                'class': 'YOLO',
                'args': {'model': 'yolov8n.pt'},
                'version': '1.0.0',
                'device_dependent': True
            },
            'yolov8s': {
                'type': 'yolo',
                'class': 'YOLO',
                'args': {'model': 'yolov8s.pt'},
                'version': '1.0.0',
                'device_dependent': True
            },
            'yolov8m': {
                'type': 'yolo',
                'class': 'YOLO',
                'args': {'model': 'yolov8m.pt'},
                'version': '1.0.0',
                'device_dependent': True
            },
            
            # OCR Models
            'easyocr': {
                'type': 'easyocr',
                'class': 'EasyOCR',
                'args': {'languages': ['en']},
                'version': '1.0.0',
                'device_dependent': True
            }
        }
        
        # Cache metadata file
        self.metadata_file = self.cache_dir / 'model_metadata.json'
        self.cache_metadata = self._load_cache_metadata()
        
        logger.info(f"Model cache manager initialized at: {self.cache_dir}")

    def _load_cache_metadata(self) -> Dict:
        """Load cache metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {}

    def _save_cache_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _get_model_cache_path(self, model_name: str, device: str = None) -> Path:
        """Get cache path for a model."""
        if device:
            return self.cache_dir / f"{model_name}_{device}.pkl"
        return self.cache_dir / f"{model_name}.pkl"

    def _get_model_info_path(self, model_name: str, device: str = None) -> Path:
        """Get info path for a model."""
        if device:
            return self.cache_dir / f"{model_name}_{device}_info.json"
        return self.cache_dir / f"{model_name}_info.json"

    def _generate_model_hash(self, model_name: str, device: str = None) -> str:
        """Generate hash for model configuration."""
        model_info = self.model_registry[model_name]
        config_str = f"{model_name}_{model_info['version']}_{device}_{json.dumps(model_info['args'], sort_keys=True)}"
        return hashlib.md5(config_str.encode()).hexdigest()

    def is_model_cached(self, model_name: str, device: str = None) -> bool:
        """Check if model is cached and up to date."""
        if model_name not in self.model_registry:
            logger.warning(f"Unknown model: {model_name}")
            return False
        
        cache_path = self._get_model_cache_path(model_name, device)
        info_path = self._get_model_info_path(model_name, device)
        
        if not cache_path.exists() or not info_path.exists():
            return False
        
        try:
            with open(info_path, 'r') as f:
                cached_info = json.load(f)
            
            current_hash = self._generate_model_hash(model_name, device)
            return cached_info.get('hash') == current_hash
            
        except Exception as e:
            logger.warning(f"Failed to check cache for {model_name}: {e}")
            return False

    def cache_model(self, model_name: str, model_instance: Any, device: str = None):
        """Cache a model instance."""
        try:
            cache_path = self._get_model_cache_path(model_name, device)
            info_path = self._get_model_info_path(model_name, device)
            
            # Save model
            with open(cache_path, 'wb') as f:
                pickle.dump(model_instance, f)
            
            # Save metadata
            model_info = {
                'model_name': model_name,
                'version': self.model_registry[model_name]['version'],
                'device': device,
                'hash': self._generate_model_hash(model_name, device),
                'cached_at': str(Path().cwd()),
                'model_type': self.model_registry[model_name]['type']
            }
            
            with open(info_path, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            logger.info(f"Cached model: {model_name} (device: {device})")
            
        except Exception as e:
            logger.error(f"Failed to cache model {model_name}: {e}")

    def load_cached_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Load a cached model."""
        try:
            cache_path = self._get_model_cache_path(model_name, device)
            
            if not cache_path.exists():
                logger.warning(f"Cache file not found: {cache_path}")
                return None
            
            with open(cache_path, 'rb') as f:
                model = pickle.load(f)
            
            logger.info(f"Loaded cached model: {model_name} (device: {device})")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load cached model {model_name}: {e}")
            return None

    def get_or_create_model(self, model_name: str, device: str = None) -> Any:
        """Get cached model or create new one."""
        if self.is_model_cached(model_name, device):
            cached_model = self.load_cached_model(model_name, device)
            if cached_model is not None:
                return cached_model
        
        logger.info(f"Creating new model: {model_name} (device: {device})")
        model = self._create_model(model_name, device)
        
        if model is not None:
            self.cache_model(model_name, model, device)
        
        return model

    def _create_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create a new model instance."""
        if model_name not in self.model_registry:
            logger.error(f"Unknown model: {model_name}")
            return None
        
        model_info = self.model_registry[model_name]
        
        try:
            if model_info['type'] == 'facenet_pytorch':
                return self._create_facenet_model(model_name, device)
            elif model_info['type'] == 'torchvision':
                return self._create_torchvision_model(model_name, device)
            elif model_info['type'] == 'opencv':
                return self._create_opencv_model(model_name, device)
            elif model_info['type'] == 'yolo':
                return self._create_yolo_model(model_name, device)
            elif model_info['type'] == 'easyocr':
                return self._create_easyocr_model(model_name, device)
            else:
                logger.error(f"Unknown model type: {model_info['type']}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create model {model_name}: {e}")
            return None

    def _create_facenet_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create FaceNet model."""
        model_info = self.model_registry[model_name]
        
        if device is None:
            device = str(torch.device(ai_config.ai_device))
        
        if model_name == 'mtcnn':
            model = MTCNN(
                device=device,
                **model_info['args']
            )
        elif model_name == 'facenet_resnet':
            model = InceptionResnetV1(**model_info['args']).eval().to(device)
        else:
            logger.error(f"Unknown FaceNet model: {model_name}")
            return None
        
        return model

    def _create_torchvision_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create TorchVision model."""
        model_info = self.model_registry[model_name]
        
        if device is None:
            device = str(torch.device(ai_config.ai_device))
        
        model_class = model_info['class']
        model = model_class(**model_info['args'])
        
        if model_info.get('device_dependent', True):
            model = model.to(device)
        
        return model

    def _create_opencv_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create OpenCV model."""
        model_info = self.model_registry[model_name]
        
        if model_name == 'opencv_hog':
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            return hog
        elif model_name == 'opencv_haar_cascade':
            # Download Haar cascade if not exists
            cascade_path = self._download_haar_cascade()
            if cascade_path:
                return cv2.CascadeClassifier(str(cascade_path))
        else:
            logger.error(f"Unknown OpenCV model: {model_name}")
            return None
        
        return None

    def _create_yolo_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create YOLO model."""
        try:
            from ultralytics import YOLO
            
            model_info = self.model_registry[model_name]
            model_path = model_info['args']['model']
            
            # YOLO will automatically download the model if not present
            model = YOLO(model_path)
            
            if device:
                model.to(device)
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to create YOLO model {model_name}: {e}")
            return None

    def _create_easyocr_model(self, model_name: str, device: str = None) -> Optional[Any]:
        """Create EasyOCR model."""
        try:
            import easyocr
            
            model_info = self.model_registry[model_name]
            languages = model_info['args']['languages']
            
            # EasyOCR will automatically download models if not present
            reader = easyocr.Reader(languages, gpu=(device == 'cuda'))
            
            return reader
            
        except Exception as e:
            logger.error(f"Failed to create EasyOCR model {model_name}: {e}")
            return None

    def _download_haar_cascade(self) -> Optional[Path]:
        """Download Haar cascade XML file."""
        cascade_name = 'haarcascade_frontalface_default.xml'
        cascade_path = self.cache_dir / cascade_name
        
        if cascade_path.exists():
            return cascade_path
        
        try:
            # Download from OpenCV GitHub
            url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{cascade_name}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(cascade_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded Haar cascade: {cascade_path}")
            return cascade_path
            
        except Exception as e:
            logger.error(f"Failed to download Haar cascade: {e}")
            return None

    def clear_cache(self, model_name: str = None):
        """Clear cache for specific model or all models."""
        try:
            if model_name:
                # Clear specific model
                pattern = f"{model_name}*"
                for file_path in self.cache_dir.glob(pattern):
                    file_path.unlink()
                logger.info(f"Cleared cache for model: {model_name}")
            else:
                # Clear all cache
                for file_path in self.cache_dir.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                logger.info("Cleared all model cache")
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            total_size = 0
            model_count = 0
            
            for file_path in self.cache_dir.glob("*.pkl"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    model_count += 1
            
            return {
                'cache_dir': str(self.cache_dir),
                'total_models': model_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'available_models': list(self.model_registry.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}

    def update_model_registry(self, new_registry: Dict):
        """Update model registry with new models."""
        self.model_registry.update(new_registry)
        logger.info(f"Updated model registry with {len(new_registry)} new models")

    def validate_cache(self) -> Dict:
        """Validate cache integrity."""
        validation_results = {}
        
        for model_name in self.model_registry.keys():
            try:
                is_valid = self.is_model_cached(model_name)
                validation_results[model_name] = {
                    'cached': is_valid,
                    'valid': is_valid
                }
            except Exception as e:
                validation_results[model_name] = {
                    'cached': False,
                    'valid': False,
                    'error': str(e)
                }
        
        return validation_results


# Global cache manager instance
_model_cache_manager = None

def get_model_cache_manager() -> ModelCacheManager:
    """Get global model cache manager instance."""
    global _model_cache_manager
    if _model_cache_manager is None:
        _model_cache_manager = ModelCacheManager()
    return _model_cache_manager


def get_cached_model(model_name: str, device: str = None) -> Any:
    """Convenience function to get cached model."""
    cache_manager = get_model_cache_manager()
    return cache_manager.get_or_create_model(model_name, device)


def clear_model_cache(model_name: str = None):
    """Convenience function to clear model cache."""
    cache_manager = get_model_cache_manager()
    cache_manager.clear_cache(model_name)
