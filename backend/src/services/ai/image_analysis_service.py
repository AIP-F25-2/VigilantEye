"""Image analysis: object detection, scene understanding, OCR."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import easyocr
import numpy as np
from PIL import Image
from ultralytics import YOLO

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class ObjectDetectionService:
    """Detect and classify objects in images using YOLO."""

    def __init__(self):
        """Initialize object detection model."""
        self.model = YOLO(ai_config.object_detection_model)
        self.confidence_threshold = ai_config.object_detection_confidence
        logger.info(f"Object detection model loaded: {ai_config.object_detection_model}")

    def detect_objects(self, image_path: str) -> Dict:
        """
        Detect objects in image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with detected objects
        """
        logger.info(f"Detecting objects in: {image_path}")
        
        try:
            # Run detection
            results = self.model(image_path, conf=self.confidence_threshold)
            
            detected_objects = []
            object_counts = {}
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Get class and confidence
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = result.names[cls]
                    
                    detected_objects.append({
                        'label': label,
                        'confidence': conf,
                        'bounding_box': {
                            'x': int(x1),
                            'y': int(y1),
                            'width': int(x2 - x1),
                            'height': int(y2 - y1)
                        }
                    })
                    
                    # Count objects
                    object_counts[label] = object_counts.get(label, 0) + 1
            
            # Special counts
            people_count = object_counts.get('person', 0)
            vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']
            vehicle_count = sum(object_counts.get(v, 0) for v in vehicle_classes)
            
            result_dict = {
                'objects': detected_objects,
                'object_counts': object_counts,
                'total_objects': len(detected_objects),
                'people_count': people_count,
                'vehicle_count': vehicle_count,
            }
            
            logger.info(
                f"Object detection completed: {len(detected_objects)} objects, "
                f"{people_count} people, {vehicle_count} vehicles"
            )
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}", exc_info=True)
            return {
                'objects': [],
                'object_counts': {},
                'total_objects': 0,
                'people_count': 0,
                'vehicle_count': 0,
                'error': str(e)
            }


class OCRService:
    """Optical Character Recognition for text detection."""

    def __init__(self):
        """Initialize OCR reader."""
        languages = ai_config.ocr_languages.split(',')
        self.reader = easyocr.Reader(languages, gpu=(ai_config.ai_device == 'cuda'))
        logger.info(f"OCR service initialized with languages: {languages}")

    def extract_text(self, image_path: str) -> Dict:
        """
        Extract text from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with extracted text and locations
        """
        logger.info(f"Extracting text from: {image_path}")
        
        try:
            # Read text
            results = self.reader.readtext(image_path)
            
            detected_texts = []
            all_text = []
            
            for (bbox, text, confidence) in results:
                # Get bounding box
                (tl, tr, br, bl) = bbox
                x = int(min(tl[0], bl[0]))
                y = int(min(tl[1], tr[1]))
                w = int(max(tr[0], br[0]) - x)
                h = int(max(bl[1], br[1]) - y)
                
                detected_texts.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bounding_box': {
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h
                    }
                })
                
                all_text.append(text)
            
            result_dict = {
                'detected_texts': detected_texts,
                'full_text': ' '.join(all_text),
                'text_count': len(detected_texts),
                'has_text': len(detected_texts) > 0
            }
            
            logger.info(
                f"Text extraction completed: {len(detected_texts)} text regions found"
            )
            
            return result_dict
            
        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            return {
                'detected_texts': [],
                'full_text': '',
                'text_count': 0,
                'has_text': False,
                'error': str(e)
            }


class SceneAnalysisService:
    """Analyze scene/environment in images."""

    def __init__(self):
        """Initialize scene analysis."""
        logger.info("Scene analysis service initialized")

    def analyze_scene(self, image_path: str, detected_objects: List[Dict]) -> Dict:
        """
        Analyze scene based on image and detected objects.
        
        Args:
            image_path: Path to image file
            detected_objects: List of detected objects
            
        Returns:
            Dictionary with scene analysis
        """
        logger.info(f"Analyzing scene: {image_path}")
        
        try:
            # Load image for basic analysis
            image = cv2.imread(image_path)
            height, width = image.shape[:2]
            
            # Analyze lighting
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            lighting = self._determine_lighting(avg_brightness)
            
            # Determine location type from objects
            location_type = self._determine_location(detected_objects)
            
            # Determine time of day
            time_of_day = self._determine_time_of_day(avg_brightness, lighting)
            
            # Detect weather indicators
            weather = self._detect_weather(detected_objects, avg_brightness)
            
            result = {
                'location_type': location_type,
                'time_of_day': time_of_day,
                'weather_conditions': weather,
                'lighting_quality': lighting,
                'image_dimensions': {'width': width, 'height': height},
                'average_brightness': float(avg_brightness)
            }
            
            logger.info(
                f"Scene analysis completed: {location_type}, {time_of_day}, {lighting}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {e}", exc_info=True)
            return {
                'location_type': 'unknown',
                'time_of_day': 'unknown',
                'weather_conditions': 'unknown',
                'lighting_quality': 'unknown',
                'error': str(e)
            }

    def _determine_lighting(self, brightness: float) -> str:
        """Determine lighting quality."""
        if brightness < 50:
            return "dark"
        elif brightness < 100:
            return "dim"
        elif brightness < 150:
            return "moderate"
        elif brightness < 200:
            return "bright"
        else:
            return "very bright"

    def _determine_time_of_day(self, brightness: float, lighting: str) -> str:
        """Determine time of day."""
        if brightness < 80:
            return "nighttime"
        elif brightness < 120:
            return "dusk/dawn"
        else:
            return "daytime"

    def _determine_location(self, objects: List[Dict]) -> str:
        """Determine location type from objects."""
        object_labels = [obj['label'] for obj in objects]
        
        indoor_indicators = ['couch', 'bed', 'tv', 'chair', 'table', 'laptop']
        outdoor_indicators = ['car', 'tree', 'road', 'sky', 'building']
        office_indicators = ['chair', 'laptop', 'desk', 'monitor']
        
        indoor_count = sum(1 for obj in object_labels if obj in indoor_indicators)
        outdoor_count = sum(1 for obj in object_labels if obj in outdoor_indicators)
        office_count = sum(1 for obj in object_labels if obj in office_indicators)
        
        if office_count >= 2:
            return "office/workplace"
        elif indoor_count > outdoor_count:
            return "indoor"
        elif outdoor_count > 0:
            return "outdoor"
        else:
            return "unknown"

    def _detect_weather(self, objects: List[Dict], brightness: float) -> str:
        """Detect weather conditions."""
        object_labels = [obj['label'] for obj in objects]
        
        if 'umbrella' in object_labels:
            return "rainy"
        elif brightness > 180:
            return "sunny"
        elif brightness < 100:
            return "overcast/cloudy"
        else:
            return "clear"


def analyze_image_complete(image_path: str, frame_timestamp_ms: int = 0) -> Dict:
    """
    Complete image analysis: objects, OCR, and scene.
    
    This function is designed to be called in a thread.
    
    Args:
        image_path: Path to image file
        frame_timestamp_ms: Timestamp of frame in video
        
    Returns:
        Combined analysis results
    """
    logger.info(f"Starting complete image analysis: {image_path}")
    
    try:
        # Initialize services
        object_detector = ObjectDetectionService()
        ocr_service = OCRService()
        scene_analyzer = SceneAnalysisService()
        
        # Run analyses
        object_results = object_detector.detect_objects(image_path)
        ocr_results = ocr_service.extract_text(image_path)
        scene_results = scene_analyzer.analyze_scene(
            image_path,
            object_results.get('objects', [])
        )
        
        # Generate combined description
        combined_description = generate_image_description(
            object_results,
            ocr_results,
            scene_results
        )
        
        result = {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'objects': object_results,
            'text': ocr_results,
            'scene': scene_results,
            'combined_description': combined_description,
            'status': 'completed'
        }
        
        logger.info(f"Image analysis completed: {image_path}")
        return result
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)
        return {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'status': 'failed',
            'error': str(e)
        }


def generate_image_description(
    object_results: Dict,
    ocr_results: Dict,
    scene_results: Dict
) -> str:
    """Generate natural language description of image."""
    parts = []
    
    # Scene description
    location = scene_results.get('location_type', 'unknown')
    time = scene_results.get('time_of_day', 'unknown')
    weather = scene_results.get('weather_conditions', 'unknown')
    
    parts.append(f"A {time} scene in a {location} location with {weather} conditions.")
    
    # Objects
    object_counts = object_results.get('object_counts', {})
    if object_counts:
        top_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        object_desc = ', '.join([f"{count} {obj}(s)" for obj, count in top_objects])
        parts.append(f"The image contains: {object_desc}.")
    
    # People
    people_count = object_results.get('people_count', 0)
    if people_count > 0:
        parts.append(f"There are {people_count} person(s) visible in the scene.")
    
    # Text
    if ocr_results.get('has_text'):
        text = ocr_results.get('full_text', '')[:100]
        parts.append(f"Visible text: \"{text}...\"")
    
    return ' '.join(parts)
