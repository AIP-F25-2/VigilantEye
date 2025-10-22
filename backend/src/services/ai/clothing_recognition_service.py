"""Clothing and appearance recognition service for person identification."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
import torchvision.models as models

from src.config.ai_config import AIConfig
from src.services.ai.model_cache_manager import get_cached_model
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class ClothingRecognitionService:
    """Recognize people based on clothing and appearance when faces are not visible."""

    def __init__(self):
        """Initialize clothing recognition models."""
        self.device = torch.device(ai_config.ai_device)
        
        # Load pre-trained models for clothing analysis
        self.clothing_model = self._load_clothing_model()
        self.color_model = self._load_color_model()
        self.texture_model = self._load_texture_model()
        
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Clothing categories
        self.clothing_categories = [
            'shirt', 'pants', 'dress', 'jacket', 'coat', 'sweater', 'hoodie',
            'shorts', 'skirt', 'blouse', 't-shirt', 'polo', 'tank_top', 'suit',
            'uniform', 'work_clothes', 'casual', 'formal', 'sportswear'
        ]
        
        # Color categories
        self.color_categories = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple',
            'pink', 'brown', 'gray', 'navy', 'maroon', 'beige', 'cream', 'tan'
        ]
        
        # Texture patterns
        self.texture_patterns = [
            'solid', 'striped', 'checkered', 'polka_dot', 'floral', 'plaid',
            'denim', 'leather', 'suede', 'cotton', 'wool', 'silk', 'linen'
        ]
        
    def __init__(self):
        """Initialize clothing recognition models."""
        self.device = torch.device(ai_config.ai_device)
        
        # Load cached models or create new ones
        self.clothing_model = get_cached_model('resnet50', str(self.device))
        self.color_model = get_cached_model('resnet18', str(self.device))
        self.texture_model = get_cached_model('efficientnet_b0', str(self.device))
        
        if self.clothing_model is None or self.color_model is None or self.texture_model is None:
            logger.error("Failed to load clothing recognition models")
            raise RuntimeError("Clothing recognition models could not be loaded")
        
        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        logger.info("Clothing recognition service initialized with cached models")


    def detect_person_regions(self, image_path: str) -> List[Dict]:
        """
        Detect person regions in image using YOLO or similar.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of person bounding boxes
        """
        logger.info(f"Detecting person regions in: {image_path}")
        
        try:
            # Load image
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Simple person detection using OpenCV HOG
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Detect people
            boxes, weights = hog.detectMultiScale(
                image_rgb,
                winStride=(8, 8),
                padding=(32, 32),
                scale=1.05,
                hitThreshold=0.0,
                finalThreshold=2.0
            )
            
            person_regions = []
            for i, (x, y, w, h) in enumerate(boxes):
                person_regions.append({
                    'person_index': i,
                    'bounding_box': {
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h)
                    },
                    'confidence': float(weights[i][0]) if len(weights) > i else 0.5
                })
            
            logger.info(f"Detected {len(person_regions)} person regions")
            return person_regions
            
        except Exception as e:
            logger.error(f"Person detection failed: {e}", exc_info=True)
            return []

    def analyze_clothing(self, image_path: str, person_box: Dict) -> Dict:
        """
        Analyze clothing in person region.
        
        Args:
            image_path: Path to image file
            person_box: Person bounding box
            
        Returns:
            Clothing analysis results
        """
        try:
            # Load and crop person region
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            x = person_box['x']
            y = person_box['y']
            w = person_box['width']
            h = person_box['height']
            
            # Crop person region
            person_crop = image_rgb[y:y+h, x:x+w]
            
            # Convert to PIL Image
            person_pil = Image.fromarray(person_crop)
            
            # Analyze clothing
            clothing_analysis = self._analyze_clothing_types(person_pil)
            color_analysis = self._analyze_colors(person_crop)
            texture_analysis = self._analyze_textures(person_pil)
            
            # Generate clothing signature
            clothing_signature = self._generate_clothing_signature(
                clothing_analysis, color_analysis, texture_analysis
            )
            
            return {
                'clothing_types': clothing_analysis,
                'colors': color_analysis,
                'textures': texture_analysis,
                'clothing_signature': clothing_signature,
                'person_box': person_box
            }
            
        except Exception as e:
            logger.error(f"Clothing analysis failed: {e}")
            return {
                'clothing_types': {},
                'colors': {},
                'textures': {},
                'clothing_signature': None,
                'person_box': person_box,
                'error': str(e)
            }

    def _analyze_clothing_types(self, image: Image.Image) -> Dict:
        """Analyze clothing types in image."""
        try:
            if self.clothing_model is None:
                # Fallback: simple heuristic analysis
                return self._heuristic_clothing_analysis(image)
            
            # Preprocess image
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.clothing_model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
            
            # Get top clothing predictions
            top_probs, top_indices = torch.topk(probabilities, 5)
            
            clothing_results = {}
            for i in range(len(top_indices[0])):
                category = self.clothing_categories[top_indices[0][i]]
                confidence = float(top_probs[0][i])
                clothing_results[category] = confidence
            
            return clothing_results
            
        except Exception as e:
            logger.error(f"Clothing type analysis failed: {e}")
            return {}

    def _analyze_colors(self, image: np.ndarray) -> Dict:
        """Analyze dominant colors in person region."""
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            
            # Calculate color histogram
            hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Find dominant colors
            dominant_colors = self._extract_dominant_colors(image)
            
            # Analyze color distribution
            color_analysis = {
                'dominant_colors': dominant_colors,
                'brightness': float(np.mean(hist_v)),
                'saturation': float(np.mean(hist_s)),
                'color_distribution': self._analyze_color_distribution(image)
            }
            
            return color_analysis
            
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {}

    def _analyze_textures(self, image: Image.Image) -> Dict:
        """Analyze texture patterns in clothing."""
        try:
            if self.texture_model is None:
                # Fallback: simple texture analysis
                return self._heuristic_texture_analysis(image)
            
            # Preprocess image
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Get texture predictions
            with torch.no_grad():
                outputs = self.texture_model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
            
            # Get top texture predictions
            top_probs, top_indices = torch.topk(probabilities, 3)
            
            texture_results = {}
            for i in range(len(top_indices[0])):
                pattern = self.texture_patterns[top_indices[0][i]]
                confidence = float(top_probs[0][i])
                texture_results[pattern] = confidence
            
            return texture_results
            
        except Exception as e:
            logger.error(f"Texture analysis failed: {e}")
            return {}

    def _extract_dominant_colors(self, image: np.ndarray, k: int = 5) -> List[Dict]:
        """Extract dominant colors using K-means clustering."""
        try:
            # Reshape image to list of pixels
            pixels = image.reshape(-1, 3)
            
            # Apply K-means clustering
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get cluster centers (dominant colors)
            colors = kmeans.cluster_centers_
            labels = kmeans.labels_
            
            # Calculate color percentages
            color_counts = np.bincount(labels)
            color_percentages = color_counts / len(labels)
            
            dominant_colors = []
            for i, color in enumerate(colors):
                dominant_colors.append({
                    'rgb': [int(c) for c in color],
                    'percentage': float(color_percentages[i]),
                    'color_name': self._rgb_to_color_name(color)
                })
            
            return dominant_colors
            
        except Exception as e:
            logger.error(f"Dominant color extraction failed: {e}")
            return []

    def _rgb_to_color_name(self, rgb: np.ndarray) -> str:
        """Convert RGB values to color name."""
        r, g, b = rgb
        
        # Simple color mapping
        if r > 200 and g < 100 and b < 100:
            return 'red'
        elif r < 100 and g > 200 and b < 100:
            return 'green'
        elif r < 100 and g < 100 and b > 200:
            return 'blue'
        elif r > 200 and g > 200 and b < 100:
            return 'yellow'
        elif r > 200 and g < 200 and b > 200:
            return 'purple'
        elif r > 200 and g > 200 and b > 200:
            return 'white'
        elif r < 50 and g < 50 and b < 50:
            return 'black'
        elif r > 150 and g > 100 and b < 100:
            return 'orange'
        elif r > 200 and g > 150 and b > 150:
            return 'pink'
        elif r > 100 and g > 50 and b < 50:
            return 'brown'
        elif r > 100 and g > 100 and b > 100:
            return 'gray'
        else:
            return 'unknown'

    def _analyze_color_distribution(self, image: np.ndarray) -> Dict:
        """Analyze overall color distribution."""
        try:
            # Calculate mean RGB values
            mean_rgb = np.mean(image, axis=(0, 1))
            
            # Calculate color variance
            color_variance = np.var(image, axis=(0, 1))
            
            # Calculate brightness
            brightness = np.mean(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
            
            return {
                'mean_rgb': [float(c) for c in mean_rgb],
                'color_variance': [float(v) for v in color_variance],
                'brightness': float(brightness),
                'is_dark': brightness < 100,
                'is_bright': brightness > 200,
                'is_colorful': np.mean(color_variance) > 1000
            }
            
        except Exception as e:
            logger.error(f"Color distribution analysis failed: {e}")
            return {}

    def _generate_clothing_signature(
        self,
        clothing_types: Dict,
        colors: Dict,
        textures: Dict
    ) -> str:
        """Generate a unique signature for clothing combination."""
        try:
            # Extract top clothing type
            top_clothing = max(clothing_types.items(), key=lambda x: x[1])[0] if clothing_types else 'unknown'
            
            # Extract dominant color
            dominant_color = 'unknown'
            if colors.get('dominant_colors'):
                dominant_color = colors['dominant_colors'][0]['color_name']
            
            # Extract top texture
            top_texture = max(textures.items(), key=lambda x: x[1])[0] if textures else 'solid'
            
            # Generate signature
            signature = f"{top_clothing}_{dominant_color}_{top_texture}"
            
            # Add brightness indicator
            if colors.get('color_distribution', {}).get('is_dark'):
                signature += "_dark"
            elif colors.get('color_distribution', {}).get('is_bright'):
                signature += "_bright"
            
            return signature
            
        except Exception as e:
            logger.error(f"Clothing signature generation failed: {e}")
            return "unknown_unknown_solid"

    def _heuristic_clothing_analysis(self, image: Image.Image) -> Dict:
        """Fallback heuristic clothing analysis."""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Simple analysis based on image regions
            height, width = img_array.shape[:2]
            
            # Analyze upper body (shirt area)
            upper_region = img_array[:height//2, :]
            upper_colors = self._analyze_region_colors(upper_region)
            
            # Analyze lower body (pants area)
            lower_region = img_array[height//2:, :]
            lower_colors = self._analyze_region_colors(lower_region)
            
            return {
                'shirt': 0.8 if upper_colors['is_dark'] else 0.6,
                'pants': 0.8 if lower_colors['is_dark'] else 0.6,
                'casual': 0.7,
                'unknown': 0.3
            }
            
        except Exception as e:
            logger.error(f"Heuristic clothing analysis failed: {e}")
            return {}

    def _heuristic_texture_analysis(self, image: Image.Image) -> Dict:
        """Fallback heuristic texture analysis."""
        try:
            # Convert to grayscale for texture analysis
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            
            # Calculate texture features
            texture_variance = np.var(gray)
            
            if texture_variance < 500:
                return {'solid': 0.9, 'smooth': 0.7}
            elif texture_variance < 1500:
                return {'striped': 0.6, 'checkered': 0.4}
            else:
                return {'patterned': 0.8, 'textured': 0.6}
                
        except Exception as e:
            logger.error(f"Heuristic texture analysis failed: {e}")
            return {'solid': 0.5}

    def _analyze_region_colors(self, region: np.ndarray) -> Dict:
        """Analyze colors in a specific region."""
        try:
            mean_color = np.mean(region, axis=(0, 1))
            brightness = np.mean(cv2.cvtColor(region, cv2.COLOR_RGB2GRAY))
            
            return {
                'mean_rgb': [float(c) for c in mean_color],
                'brightness': float(brightness),
                'is_dark': brightness < 100,
                'is_bright': brightness > 200
            }
            
        except Exception as e:
            logger.error(f"Region color analysis failed: {e}")
            return {}

    def process_person(self, image_path: str, person_data: Dict) -> Dict:
        """
        Complete person processing: detection, clothing analysis, and signature generation.
        
        Args:
            image_path: Path to image file
            person_data: Person detection data with bounding box
            
        Returns:
            Complete person analysis
        """
        try:
            # Analyze clothing
            clothing_analysis = self.analyze_clothing(
                image_path,
                person_data['bounding_box']
            )
            
            # Generate person ID
            person_id = f"person_{uuid.uuid4().hex[:12]}"
            
            result = {
                'person_id': person_id,
                'bounding_box': person_data['bounding_box'],
                'confidence': person_data['confidence'],
                **clothing_analysis
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Person processing failed: {e}", exc_info=True)
            return {
                'person_id': None,
                'bounding_box': person_data['bounding_box'],
                'error': str(e)
            }


def analyze_persons_in_image(image_path: str, frame_timestamp_ms: int = 0) -> Dict:
    """
    Analyze all persons in an image based on clothing and appearance.
    
    This function is designed to be called in a thread.
    
    Args:
        image_path: Path to image file
        frame_timestamp_ms: Timestamp of frame in video
        
    Returns:
        Dictionary with all person analyses
    """
    logger.info(f"Analyzing persons in: {image_path}")
    
    try:
        service = ClothingRecognitionService()
        
        # Detect person regions
        persons = service.detect_person_regions(image_path)
        
        if not persons:
            return {
                'image_path': image_path,
                'frame_timestamp_ms': frame_timestamp_ms,
                'person_count': 0,
                'persons': [],
                'status': 'completed'
            }
        
        # Process each person
        processed_persons = []
        for person in persons:
            processed = service.process_person(image_path, person)
            processed['frame_timestamp_ms'] = frame_timestamp_ms
            processed_persons.append(processed)
        
        result = {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'person_count': len(processed_persons),
            'persons': processed_persons,
            'status': 'completed'
        }
        
        logger.info(
            f"Person analysis completed: {len(processed_persons)} persons processed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Person analysis failed: {e}", exc_info=True)
        return {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'person_count': 0,
            'persons': [],
            'status': 'failed',
            'error': str(e)
        }
