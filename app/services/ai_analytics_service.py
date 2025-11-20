"""
AI Analytics Service for VigilantEye
Provides object detection, anomaly detection, behavior analysis, and smart alerts
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

# Try to import AI/ML dependencies
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    logging.warning("OpenCV not available. Some AI features will be limited.")

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    DBSCAN = None
    StandardScaler = None

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    UNUSUAL_MOTION = "unusual_motion"
    CROWD_DENSITY = "crowd_density"
    LOITERING = "loitering"
    RAPID_MOVEMENT = "rapid_movement"
    OBJECT_LEFT = "object_left"
    OBJECT_REMOVED = "object_removed"
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class BehaviorType(Enum):
    """Types of behaviors that can be recognized"""
    WALKING = "walking"
    RUNNING = "running"
    STANDING = "standing"
    SITTING = "sitting"
    LOITERING = "loitering"
    CROWD_GATHERING = "crowd_gathering"
    VEHICLE_MOVEMENT = "vehicle_movement"
    UNKNOWN = "unknown"

@dataclass
class DetectedObject:
    """Represents a detected object"""
    object_type: str
    confidence: float
    bounding_box: List[int]  # [x, y, width, height]
    center: Tuple[int, int]
    area: float

@dataclass
class AnomalyDetection:
    """Represents an anomaly detection result"""
    anomaly_type: AnomalyType
    confidence: float
    location: Tuple[int, int]
    timestamp: datetime
    description: str
    metadata: Dict

@dataclass
class BehaviorAnalysis:
    """Represents behavior analysis result"""
    behavior_type: BehaviorType
    confidence: float
    duration_seconds: float
    location: Tuple[int, int]
    metadata: Dict

class ObjectDetector:
    """Object detection using OpenCV and basic ML"""
    
    def __init__(self):
        self.enabled = CV2_AVAILABLE
        if not self.enabled:
            logger.warning("ObjectDetector disabled: OpenCV not available")
            return
        
        # Initialize object detection (using OpenCV's DNN or basic detection)
        self.detected_objects_history = []
        self.object_tracking = {}  # Track objects across frames
    
    def detect_objects(self, frame: Any, min_confidence: float = 0.3, use_motion: bool = False) -> List[DetectedObject]:
        """Detect objects in a frame using OpenCV"""
        if not self.enabled or not CV2_AVAILABLE:
            return []
        
        if frame is None:
            logger.warning("ObjectDetector: frame is None")
            return []
        
        try:
            # Validate frame shape
            if not hasattr(frame, 'shape') or len(frame.shape) < 2:
                logger.warning(f"ObjectDetector: invalid frame shape: {type(frame)}")
                return []
            
            # Convert to grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            detected_objects = []
            
            # For single images, use edge detection and contour analysis
            # For video streams, use background subtraction
            if use_motion and hasattr(self, 'bg_subtractor'):
                # Use background subtractor for motion detection (video)
                fg_mask = self.bg_subtractor.apply(gray)
                contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            else:
                # For single images, use edge detection and adaptive thresholding
                # Apply Gaussian blur to reduce noise
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Use adaptive threshold to find objects
                thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                             cv2.THRESH_BINARY_INV, 11, 2)
                
                # Find contours
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Process detected contours
            for contour in contours:
                area = cv2.contourArea(contour)
                # Adjust threshold based on frame size
                min_area = max(500, (frame.shape[0] * frame.shape[1]) / 1000)  # At least 0.1% of frame
                
                if area > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    center = (x + w // 2, y + h // 2)
                    
                    # Classify object type based on size and shape
                    object_type = self._classify_object(area, w, h)
                    
                    # Calculate confidence based on area and shape regularity
                    aspect_ratio = w / h if h > 0 else 1
                    shape_regularity = min(1.0, area / (w * h)) if w > 0 and h > 0 else 0.5
                    confidence = min(0.9, (area / 10000) * shape_regularity)
                    
                    if confidence >= min_confidence:
                        detected_objects.append(DetectedObject(
                            object_type=object_type,
                            confidence=confidence,
                            bounding_box=[x, y, w, h],
                            center=center,
                            area=area
                        ))
            
            return detected_objects
            
        except Exception as e:
            logger.error(f"Error in object detection: {e}", exc_info=True)
            return []
    
    def _classify_object(self, area: float, width: int, height: int) -> str:
        """Classify object type based on characteristics"""
        aspect_ratio = width / height if height > 0 else 1
        
        if area < 2000:
            return "small_object"
        elif area > 50000:
            return "large_object"
        elif aspect_ratio > 2.0:
            return "vehicle"
        elif aspect_ratio < 0.5:
            return "person_standing"
        else:
            return "person"

class AnomalyDetector:
    """Detect anomalies in video feeds"""
    
    def __init__(self, sensitivity: float = 0.7):
        self.sensitivity = sensitivity
        self.enabled = CV2_AVAILABLE
        self.motion_history = []
        self.object_positions = {}  # Track object positions over time
        self.background_model = None
        
        if not self.enabled:
            logger.warning("AnomalyDetector disabled: OpenCV not available")
    
    def detect_anomalies(self, frame: Any, detected_objects: List[DetectedObject],
                        frame_number: int, timestamp: datetime) -> List[AnomalyDetection]:
        """Detect anomalies in the current frame"""
        if not self.enabled:
            return []
        
        anomalies = []
        
        try:
            # 1. Detect unusual motion patterns
            motion_anomalies = self._detect_unusual_motion(frame, detected_objects, frame_number)
            anomalies.extend(motion_anomalies)
            
            # 2. Detect loitering
            loitering_anomalies = self._detect_loitering(detected_objects, timestamp)
            anomalies.extend(loitering_anomalies)
            
            # 3. Detect rapid movement
            rapid_movement = self._detect_rapid_movement(detected_objects, frame_number)
            anomalies.extend(rapid_movement)
            
            # 4. Detect crowd density
            crowd_anomalies = self._detect_crowd_density(detected_objects, frame)
            anomalies.extend(crowd_anomalies)
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
        
        return anomalies
    
    def _detect_unusual_motion(self, frame: Any, objects: List[DetectedObject],
                              frame_number: int) -> List[AnomalyDetection]:
        """Detect unusual motion patterns"""
        anomalies = []
        
        if len(objects) == 0:
            return anomalies
        
        # Store motion data
        motion_data = {
            'frame': frame_number,
            'object_count': len(objects),
            'total_area': sum(obj.area for obj in objects)
        }
        self.motion_history.append(motion_data)
        
        # Keep only last 100 frames
        if len(self.motion_history) > 100:
            self.motion_history.pop(0)
        
        # Detect sudden changes
        if len(self.motion_history) > 10:
            recent_avg = sum(m['object_count'] for m in self.motion_history[-10:]) / 10
            current_count = len(objects)
            
            if current_count > recent_avg * 2:  # Sudden increase
                anomalies.append(AnomalyDetection(
                    anomaly_type=AnomalyType.UNUSUAL_MOTION,
                    confidence=min(0.9, (current_count - recent_avg) / recent_avg),
                    location=objects[0].center if objects else (0, 0),
                    timestamp=datetime.now(),
                    description=f"Unusual motion detected: {current_count} objects vs avg {recent_avg:.1f}",
                    metadata={'object_count': current_count, 'average': recent_avg}
                ))
        
        return anomalies
    
    def _detect_loitering(self, objects: List[DetectedObject],
                         timestamp: datetime) -> List[AnomalyDetection]:
        """Detect loitering (objects staying in same area too long)"""
        anomalies = []
        loitering_threshold = 30  # seconds
        
        for obj in objects:
            obj_id = id(obj)  # Simple ID based on object instance
            
            if obj_id not in self.object_positions:
                self.object_positions[obj_id] = {
                    'first_seen': timestamp,
                    'positions': [],
                    'last_position': obj.center
                }
            
            track = self.object_positions[obj_id]
            track['positions'].append({
                'position': obj.center,
                'timestamp': timestamp
            })
            
            # Keep only last 60 seconds
            track['positions'] = [
                p for p in track['positions']
                if (timestamp - p['timestamp']).total_seconds() < 60
            ]
            
            # Check if object has been in similar location for too long
            if len(track['positions']) > 10:
                positions = [p['position'] for p in track['positions']]
                # Calculate position variance
                if positions:
                    x_coords = [p[0] for p in positions]
                    y_coords = [p[1] for p in positions]
                    # Calculate variance manually if numpy not available
                    if np is not None:
                        x_variance = np.var(x_coords) if len(x_coords) > 1 else 0
                        y_variance = np.var(y_coords) if len(y_coords) > 1 else 0
                    else:
                        # Manual variance calculation
                        def calc_variance(values):
                            if len(values) < 2:
                                return 0
                            mean = sum(values) / len(values)
                            return sum((x - mean)**2 for x in values) / len(values)
                        x_variance = calc_variance(x_coords)
                        y_variance = calc_variance(y_coords)
                    
                    # Low variance = staying in same place
                    if x_variance < 1000 and y_variance < 1000:
                        duration = (timestamp - track['first_seen']).total_seconds()
                        if duration > loitering_threshold:
                            anomalies.append(AnomalyDetection(
                                anomaly_type=AnomalyType.LOITERING,
                                confidence=min(0.95, duration / loitering_threshold),
                                location=obj.center,
                                timestamp=timestamp,
                                description=f"Loitering detected: object in same area for {duration:.1f}s",
                                metadata={'duration_seconds': duration, 'object_type': obj.object_type}
                            ))
        
        return anomalies
    
    def _detect_rapid_movement(self, objects: List[DetectedObject],
                              frame_number: int) -> List[AnomalyDetection]:
        """Detect rapid movement"""
        anomalies = []
        rapid_threshold = 50  # pixels per frame
        
        for obj in objects:
            obj_id = id(obj)
            if obj_id in self.object_positions and len(self.object_positions[obj_id]['positions']) > 1:
                positions = self.object_positions[obj_id]['positions']
                if len(positions) >= 2:
                    last_pos = positions[-1]['position']
                    prev_pos = positions[-2]['position']
                    
                    # Calculate distance
                    dx = last_pos[0] - prev_pos[0]
                    dy = last_pos[1] - prev_pos[1]
                    distance = (dx**2 + dy**2)**0.5
                    
                    if distance > rapid_threshold:
                        anomalies.append(AnomalyDetection(
                            anomaly_type=AnomalyType.RAPID_MOVEMENT,
                            confidence=min(0.9, distance / (rapid_threshold * 2)),
                            location=obj.center,
                            timestamp=datetime.now(),
                            description=f"Rapid movement detected: {distance:.1f} pixels/frame",
                            metadata={'speed': distance, 'object_type': obj.object_type}
                        ))
        
        return anomalies
    
    def _detect_crowd_density(self, objects: List[DetectedObject], frame: Any) -> List[AnomalyDetection]:
        """Detect high crowd density"""
        anomalies = []
        
        person_objects = [obj for obj in objects if 'person' in obj.object_type.lower()]
        person_count = len(person_objects)
        
        if person_count > 10:  # Threshold for crowd
            # Calculate density
            frame_area = frame.shape[0] * frame.shape[1] if frame is not None else 1
            person_area = sum(obj.area for obj in person_objects)
            density = person_area / frame_area if frame_area > 0 else 0
            
            if density > 0.3:  # 30% of frame covered by people
                anomalies.append(AnomalyDetection(
                    anomaly_type=AnomalyType.CROWD_DENSITY,
                    confidence=min(0.95, density),
                    location=(frame.shape[1] // 2, frame.shape[0] // 2) if frame is not None else (0, 0),
                    timestamp=datetime.now(),
                    description=f"High crowd density: {person_count} people, {density*100:.1f}% coverage",
                    metadata={'person_count': person_count, 'density': density}
                ))
        
        return anomalies

class BehaviorAnalyzer:
    """Analyze behaviors in video feeds"""
    
    def __init__(self):
        self.enabled = CV2_AVAILABLE
        self.behavior_history = {}  # Track behaviors over time
        
        if not self.enabled:
            logger.warning("BehaviorAnalyzer disabled: OpenCV not available")
    
    def analyze_behavior(self, objects: List[DetectedObject],
                         frame_number: int, timestamp: datetime) -> List[BehaviorAnalysis]:
        """Analyze behaviors from detected objects"""
        if not self.enabled:
            return []
        
        behaviors = []
        
        try:
            person_objects = [obj for obj in objects if 'person' in obj.object_type.lower()]
            
            # Analyze individual behaviors
            for obj in person_objects:
                behavior = self._classify_behavior(obj, frame_number, timestamp)
                if behavior:
                    behaviors.append(behavior)
            
            # Analyze group behaviors
            if len(person_objects) > 1:
                group_behavior = self._analyze_group_behavior(person_objects, timestamp)
                if group_behavior:
                    behaviors.append(group_behavior)
            
        except Exception as e:
            logger.error(f"Error in behavior analysis: {e}")
        
        return behaviors
    
    def _classify_behavior(self, obj: DetectedObject, frame_number: int,
                          timestamp: datetime) -> Optional[BehaviorAnalysis]:
        """Classify individual behavior"""
        obj_id = id(obj)
        
        if obj_id not in self.behavior_history:
            self.behavior_history[obj_id] = {
                'positions': [],
                'speeds': [],
                'first_seen': timestamp
            }
        
        history = self.behavior_history[obj_id]
        history['positions'].append({
            'position': obj.center,
            'timestamp': timestamp,
            'frame': frame_number
        })
        
        # Keep only last 30 frames
        if len(history['positions']) > 30:
            history['positions'].pop(0)
        
        if len(history['positions']) < 5:
            return None  # Need more data
        
        # Calculate average speed
        positions = history['positions']
        if len(positions) >= 2:
            total_distance = 0
            total_time = 0
            for i in range(1, len(positions)):
                p1 = positions[i-1]['position']
                p2 = positions[i]['position']
                # Calculate distance
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                distance = (dx**2 + dy**2)**0.5
                time_diff = (positions[i]['timestamp'] - positions[i-1]['timestamp']).total_seconds()
                if time_diff > 0:
                    total_distance += distance
                    total_time += time_diff
            
            avg_speed = total_distance / total_time if total_time > 0 else 0
            
            # Classify based on speed
            if avg_speed < 5:
                behavior_type = BehaviorType.STANDING
                confidence = 0.8
            elif avg_speed < 20:
                behavior_type = BehaviorType.WALKING
                confidence = 0.7
            elif avg_speed < 50:
                behavior_type = BehaviorType.RUNNING
                confidence = 0.75
            else:
                behavior_type = BehaviorType.UNKNOWN
                confidence = 0.5
            
            duration = (timestamp - history['first_seen']).total_seconds()
            
            return BehaviorAnalysis(
                behavior_type=behavior_type,
                confidence=confidence,
                duration_seconds=duration,
                location=obj.center,
                metadata={'avg_speed': avg_speed, 'object_type': obj.object_type}
            )
        
        return None
    
    def _analyze_group_behavior(self, person_objects: List[DetectedObject],
                               timestamp: datetime) -> Optional[BehaviorAnalysis]:
        """Analyze group behaviors"""
        if len(person_objects) < 3:
            return None
        
        # Check if people are clustered (crowd gathering)
        if SKLEARN_AVAILABLE and len(person_objects) > 2:
            try:
                positions = np.array([obj.center for obj in person_objects])
                scaler = StandardScaler()
                positions_scaled = scaler.fit_transform(positions)
                
                # Use DBSCAN to find clusters
                clustering = DBSCAN(eps=0.5, min_samples=2).fit(positions_scaled)
                n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
                
                if n_clusters == 1 and len(person_objects) >= 5:
                    # Large single cluster = crowd gathering
                    return BehaviorAnalysis(
                        behavior_type=BehaviorType.CROWD_GATHERING,
                        confidence=0.8,
                        duration_seconds=0,
                        location=(int(np.mean(positions[:, 0])), int(np.mean(positions[:, 1]))),
                        metadata={'person_count': len(person_objects), 'clusters': n_clusters}
                    )
            except Exception as e:
                logger.debug(f"Error in group behavior analysis: {e}")
        
        return None

class CrowdDensityAnalyzer:
    """Analyze crowd density in video feeds"""
    
    def __init__(self):
        self.enabled = CV2_AVAILABLE
        if not self.enabled:
            logger.warning("CrowdDensityAnalyzer disabled: OpenCV not available")
    
    def analyze_density(self, frame: Any, detected_objects: List[DetectedObject]) -> Dict:
        """Analyze crowd density"""
        if not self.enabled or frame is None:
            return {
                'density_level': 'unknown',
                'person_count': 0,
                'density_percentage': 0.0,
                'areas': []
            }
        
        try:
            person_objects = [obj for obj in detected_objects if 'person' in obj.object_type.lower()]
            person_count = len(person_objects)
            
            # Calculate frame area
            frame_height, frame_width = frame.shape[:2]
            frame_area = frame_width * frame_height
            
            # Calculate person coverage
            total_person_area = sum(obj.area for obj in person_objects)
            density_percentage = (total_person_area / frame_area) * 100 if frame_area > 0 else 0
            
            # Classify density level
            if density_percentage < 10:
                density_level = 'low'
            elif density_percentage < 30:
                density_level = 'medium'
            elif density_percentage < 50:
                density_level = 'high'
            else:
                density_level = 'very_high'
            
            # Identify high-density areas
            areas = []
            if person_objects:
                # Group nearby people
                for obj in person_objects:
                    areas.append({
                        'center': obj.center,
                        'person_count': 1,
                        'area': obj.area
                    })
            
            return {
                'density_level': density_level,
                'person_count': person_count,
                'density_percentage': round(density_percentage, 2),
                'areas': areas,
                'frame_size': {'width': frame_width, 'height': frame_height}
            }
            
        except Exception as e:
            logger.error(f"Error in crowd density analysis: {e}")
            return {
                'density_level': 'error',
                'person_count': 0,
                'density_percentage': 0.0,
                'areas': []
            }

class AIAnalyticsService:
    """Main service for AI analytics features"""
    
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.anomaly_detector = AnomalyDetector()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.crowd_analyzer = CrowdDensityAnalyzer()
        self.enabled = CV2_AVAILABLE
        
        logger.info(f"AIAnalyticsService initialized (enabled: {self.enabled})")
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self.enabled
    
    def process_frame(self, frame: Any, frame_number: int = 0,
                     timestamp: Optional[datetime] = None) -> Dict:
        """Process a single frame for comprehensive AI analysis"""
        if not self.enabled:
            return {"success": False, "error": "AI Analytics service not available. OpenCV (cv2) is required."}
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Validate frame
        if frame is None:
            return {"success": False, "error": "Invalid frame: frame is None"}
        
        try:
            # Ensure frame is a numpy array
            if not hasattr(frame, 'shape'):
                return {"success": False, "error": "Invalid frame: expected numpy array or OpenCV image"}
            
            # 1. Object detection (use_motion=False for single images)
            detected_objects = self.object_detector.detect_objects(frame, use_motion=False)
            
            # 2. Anomaly detection
            anomalies = self.anomaly_detector.detect_anomalies(
                frame, detected_objects, frame_number, timestamp
            )
            
            # 3. Behavior analysis
            behaviors = self.behavior_analyzer.analyze_behavior(
                detected_objects, frame_number, timestamp
            )
            
            # 4. Crowd density analysis
            crowd_analysis = self.crowd_analyzer.analyze_density(frame, detected_objects)
            
            # Always return success, even if no objects detected (empty analysis is valid)
            return {
                "success": True,
                "frame_number": frame_number,
                "timestamp": timestamp.isoformat(),
                "objects_detected": len(detected_objects),
                "objects": [
                    {
                        "type": obj.object_type,
                        "confidence": obj.confidence,
                        "bounding_box": obj.bounding_box,
                        "center": obj.center,
                        "area": obj.area
                    } for obj in detected_objects
                ] if detected_objects else [],
                "anomalies": [
                    {
                        "type": anomaly.anomaly_type.value if hasattr(anomaly.anomaly_type, 'value') else str(anomaly.anomaly_type),
                        "confidence": anomaly.confidence,
                        "location": anomaly.location,
                        "description": anomaly.description,
                        "metadata": anomaly.metadata
                    } for anomaly in anomalies
                ] if anomalies else [],
                "behaviors": [
                    {
                        "type": behavior.behavior_type.value if hasattr(behavior.behavior_type, 'value') else str(behavior.behavior_type),
                        "confidence": behavior.confidence,
                        "duration_seconds": behavior.duration_seconds,
                        "location": behavior.location,
                        "metadata": behavior.metadata
                    } for behavior in behaviors
                ] if behaviors else [],
                "crowd_density": crowd_analysis if crowd_analysis else {
                    'density_level': 'low',
                    'person_count': 0,
                    'density_percentage': 0.0,
                    'areas': []
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def process_video(self, video_path: str, frame_skip: int = 30) -> Dict:
        """Process entire video for AI analysis"""
        if not self.enabled or not CV2_AVAILABLE:
            return {"success": False, "error": "AI Analytics service not available. OpenCV (cv2) is required."}
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": f"Could not open video: {video_path}"}
            
            all_results = []
            frame_number = 0
            total_anomalies = 0
            total_behaviors = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames for performance
                if frame_number % frame_skip != 0:
                    frame_number += 1
                    continue
                
                result = self.process_frame(frame, frame_number)
                if result.get("success"):
                    all_results.append(result)
                    total_anomalies += len(result.get("anomalies", []))
                    total_behaviors += len(result.get("behaviors", []))
                else:
                    # Log non-fatal errors but continue processing
                    logger.debug(f"Frame {frame_number} processing failed: {result.get('error', 'Unknown error')}")
                
                frame_number += 1
            
            cap.release()
            
            return {
                "success": True,
                "video_path": video_path,
                "frames_processed": len(all_results),
                "total_frames": frame_number,
                "total_anomalies": total_anomalies,
                "total_behaviors": total_behaviors,
                "results": all_results
            }
            
        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_service_status(self) -> Dict:
        """Get service status and capabilities"""
        return {
            "enabled": self.enabled,
            "object_detection": self.object_detector.enabled,
            "anomaly_detection": self.anomaly_detector.enabled,
            "behavior_analysis": self.behavior_analyzer.enabled,
            "crowd_analysis": self.crowd_analyzer.enabled,
            "opencv_available": CV2_AVAILABLE,
            "sklearn_available": SKLEARN_AVAILABLE
        }

# Global service instance
ai_analytics_service = AIAnalyticsService()

def get_ai_analytics_service():
    """Get the global AI Analytics service instance"""
    return ai_analytics_service

