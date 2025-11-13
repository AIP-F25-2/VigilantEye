"""
Face & Identity Agent for VIGILANTEye Multi-Agent Video Intelligence
Handles face detection, recognition, re-identification, and watchlist management
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import pickle
import hashlib
from pathlib import Path

# Try to import FaceAI dependencies (optional)
try:
    import cv2
    import numpy as np
    import face_recognition
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    face_recognition = None
    logger = logging.getLogger(__name__)
    logger.warning("FaceAI dependencies (cv2, numpy, face_recognition) not available. CCTV features will be disabled.")

# Import existing FaceAi service
from app.services.faceai_service import get_faceai_service
from app import db
from app.models.faceai_models import FaceDetection, FaceEncoding, DemographicsAnalysis

logger = logging.getLogger(__name__)

class PersonType(Enum):
    EMPLOYEE = "employee"
    VIP = "vip"
    SUSPECT = "suspect"
    UNKNOWN = "unknown"
    VISITOR = "visitor"

class DisguiseType(Enum):
    MASK = "mask"
    HAT = "hat"
    GLASSES = "glasses"
    BEARD = "beard"
    NONE = "none"

@dataclass
class PersonIdentity:
    """Represents a person's identity information"""
    person_id: str
    name: Optional[str] = None
    person_type: PersonType = PersonType.UNKNOWN
    face_encoding: Optional[Any] = None  # np.ndarray when available
    demographics: Optional[Dict] = None
    disguise_detected: List[DisguiseType] = None
    confidence_score: float = 0.0
    last_seen: Optional[datetime] = None
    cameras_seen: List[str] = None
    watchlist_status: bool = False
    
    def __post_init__(self):
        if self.disguise_detected is None:
            self.disguise_detected = []
        if self.cameras_seen is None:
            self.cameras_seen = []

@dataclass
class DetectionResult:
    """Result of face detection and identification"""
    frame_number: int
    timestamp: datetime
    camera_id: str
    person_identities: List[PersonIdentity]
    face_locations: List[Tuple[int, int, int, int]]
    face_encodings: List[Any]  # List[np.ndarray] when available
    demographics: List[Dict]
    disguise_analysis: List[Dict]
    processing_time_ms: float

class WatchlistManager:
    """Manages watchlists for employees, VIPs, and suspects"""
    
    def __init__(self, watchlist_dir="data/watchlists"):
        self.watchlist_dir = Path(watchlist_dir)
        self.watchlist_dir.mkdir(parents=True, exist_ok=True)
        self.watchlists = {
            PersonType.EMPLOYEE: self._load_watchlist("employees.json"),
            PersonType.VIP: self._load_watchlist("vips.json"),
            PersonType.SUSPECT: self._load_watchlist("suspects.json")
        }
        self.face_encodings_cache = {}
        if CV2_AVAILABLE:
            self._load_face_encodings()
    
    def _load_watchlist(self, filename: str) -> Dict:
        """Load watchlist from JSON file"""
        filepath = self.watchlist_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading watchlist {filename}: {e}")
        return {}
    
    def _save_watchlist(self, person_type: PersonType, data: Dict):
        """Save watchlist to JSON file"""
        filename = f"{person_type.value}s.json"
        filepath = self.watchlist_dir / filename
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving watchlist {filename}: {e}")
    
    def _load_face_encodings(self):
        """Load pre-computed face encodings for watchlist members"""
        encodings_file = self.watchlist_dir / "face_encodings.pkl"
        if encodings_file.exists():
            try:
                with open(encodings_file, 'rb') as f:
                    self.face_encodings_cache = pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading face encodings: {e}")
                self.face_encodings_cache = {}
    
    def _save_face_encodings(self):
        """Save face encodings cache"""
        encodings_file = self.watchlist_dir / "face_encodings.pkl"
        try:
            with open(encodings_file, 'wb') as f:
                pickle.dump(self.face_encodings_cache, f)
        except Exception as e:
            logger.error(f"Error saving face encodings: {e}")
    
    def add_person(self, person_type: PersonType, person_id: str, name: str, 
                   face_encoding: Any, image_path: str = None,  # np.ndarray when available
                   metadata: Dict = None) -> bool:
        """Add person to watchlist"""
        try:
            person_data = {
                "person_id": person_id,
                "name": name,
                "added_date": datetime.now().isoformat(),
                "image_path": image_path,
                "metadata": metadata or {}
            }
            
            self.watchlists[person_type][person_id] = person_data
            self.face_encodings_cache[person_id] = face_encoding
            self._save_watchlist(person_type, self.watchlists[person_type])
            self._save_face_encodings()
            
            logger.info(f"Added {person_type.value}: {name} ({person_id})")
            return True
        except Exception as e:
            logger.error(f"Error adding person to watchlist: {e}")
            return False
    
    def remove_person(self, person_id: str) -> bool:
        """Remove person from all watchlists"""
        try:
            removed = False
            for person_type in PersonType:
                if person_id in self.watchlists[person_type]:
                    del self.watchlists[person_type][person_id]
                    self._save_watchlist(person_type, self.watchlists[person_type])
                    removed = True
            
            if person_id in self.face_encodings_cache:
                del self.face_encodings_cache[person_id]
                self._save_face_encodings()
            
            return removed
        except Exception as e:
            logger.error(f"Error removing person from watchlist: {e}")
            return False
    
    def get_person_encodings(self, person_type: PersonType = None) -> Dict[str, Any]:  # Dict[str, np.ndarray] when available
        """Get face encodings for watchlist members"""
        if person_type:
            return {pid: enc for pid, enc in self.face_encodings_cache.items() 
                   if pid in self.watchlists[person_type]}
        return self.face_encodings_cache.copy()
    
    def is_on_watchlist(self, person_id: str) -> Tuple[bool, Optional[PersonType]]:
        """Check if person is on any watchlist"""
        for person_type, watchlist in self.watchlists.items():
            if person_id in watchlist:
                return True, person_type
        return False, None

class DisguiseDetector:
    """Detects disguises like masks, hats, glasses, beards"""
    
    def __init__(self):
        if not CV2_AVAILABLE:
            self.enabled = False
            return
        self.enabled = True
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.mask_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')  # Placeholder
    
    def detect_disguises(self, face_image: Any) -> List[DisguiseType]:  # np.ndarray when available
        """Detect disguises in face image"""
        if not CV2_AVAILABLE or not self.enabled:
            return [DisguiseType.NONE]
        disguises = []
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        
        # Detect eyes to check for glasses
        eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 4)
        if len(eyes) == 0:
            disguises.append(DisguiseType.GLASSES)
        
        # Detect face region for mask detection
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            x, y, w, h = faces[0]
            face_region = gray[y:y+h, x:x+w]
            
            # Simple mask detection based on lower face region
            lower_face = face_region[int(h*0.6):h, :]
            if np.mean(lower_face) < 50:  # Dark region might indicate mask
                disguises.append(DisguiseType.MASK)
        
        # Detect hat based on head region
        head_region = gray[0:int(h*0.3), :]
        if np.mean(head_region) < 30:  # Dark region might indicate hat
            disguises.append(DisguiseType.HAT)
        
        return disguises if disguises else [DisguiseType.NONE]

class CrossAgeDetector:
    """Handles cross-age face recognition and re-identification"""
    
    def __init__(self, similarity_threshold: float = 0.4):
        self.similarity_threshold = similarity_threshold
        self.age_groups = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', 
                          '(25-32)', '(38-43)', '(48-53)', '(60-100)']
    
    def calculate_age_similarity(self, age1: str, age2: str) -> float:
        """Calculate similarity between age groups"""
        if age1 == age2:
            return 1.0
        
        try:
            idx1 = self.age_groups.index(age1)
            idx2 = self.age_groups.index(age2)
            distance = abs(idx1 - idx2)
            return max(0, 1.0 - (distance / len(self.age_groups)))
        except ValueError:
            return 0.0
    
    def cross_age_compare(self, encoding1: Any, encoding2: Any,  # np.ndarray when available
                         age1: str, age2: str) -> float:
        """Compare faces across different age groups"""
        if not CV2_AVAILABLE or face_recognition is None:
            return 0.0
        # Standard face similarity
        face_similarity = 1 - face_recognition.face_distance([encoding1], encoding2)[0]
        
        # Age similarity adjustment
        age_similarity = self.calculate_age_similarity(age1, age2)
        
        # Weighted combination
        return (face_similarity * 0.7) + (age_similarity * 0.3)

class FaceIdentityAgent:
    """Main Face & Identity Agent for CCTV video processing"""
    
    def __init__(self, cctv_videos_dir="app/cctv_videos", 
                 similarity_threshold: float = 0.4,
                 privacy_mode: bool = False):
        if not CV2_AVAILABLE:
            logger.warning("Face & Identity Agent disabled: cv2 not available")
            self.enabled = False
            return
        
        self.enabled = True
        self.cctv_videos_dir = Path(cctv_videos_dir)
        self.similarity_threshold = similarity_threshold
        self.privacy_mode = privacy_mode
        
        # Initialize components
        self.faceai_service = get_faceai_service()
        self.watchlist_manager = WatchlistManager()
        self.disguise_detector = DisguiseDetector()
        self.cross_age_detector = CrossAgeDetector(similarity_threshold)
        
        # Person tracking
        self.known_persons = {}  # person_id -> PersonIdentity
        self.person_counter = 0
        self.camera_tracking = {}  # camera_id -> {person_id: last_seen}
        
        logger.info("Face & Identity Agent initialized")
    
    def process_cctv_video(self, video_path: str, camera_id: str = "camera_001",
                          frame_skip: int = 30) -> List[DetectionResult]:
        """Process CCTV video for face detection and identification"""
        if not self.enabled or not CV2_AVAILABLE:
            logger.warning("CCTV processing disabled: cv2 not available")
            return []
        logger.info(f"Processing CCTV video: {video_path}")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return []
        
        results = []
        frame_number = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames for performance
                if frame_number % frame_skip != 0:
                    frame_number += 1
                    continue
                
                # Process frame
                result = self.process_frame(frame, frame_number, camera_id)
                if result:
                    results.append(result)
                
                frame_number += 1
                
        finally:
            cap.release()
        
        logger.info(f"Processed {len(results)} frames from {video_path}")
        return results
    
    def process_frame(self, frame: Any, frame_number: int,  # np.ndarray when available
                     camera_id: str) -> Optional[DetectionResult]:
        """Process a single frame for face detection and identification"""
        start_time = time.time()
        
        try:
            # Detect faces using FaceAi service
            face_result = self.faceai_service.detect_faces(frame, show_result=False)
            if face_result.get("error") or not face_result.get("results"):
                return None
            
            face_locations = []
            face_encodings = []
            person_identities = []
            demographics_list = []
            disguise_analysis = []
            
            # Process each detected face
            for i, face_data in enumerate(face_result["results"]):
                face_location = face_data["bounding_box"]
                face_encoding = face_data["face_encoding"]
                
                # Extract face region
                top, right, bottom, left = face_location
                face_image = frame[top:bottom, left:right]
                
                # Identify person
                person_identity = self._identify_person(face_encoding, face_image, camera_id)
                person_identities.append(person_identity)
                
                # Get demographics (if privacy allows)
                demographics = self._get_demographics(face_image, person_identity)
                demographics_list.append(demographics)
                
                # Detect disguises
                disguises = self.disguise_detector.detect_disguises(face_image)
                disguise_analysis.append({
                    "disguises": [d.value for d in disguises],
                    "confidence": 0.8  # Placeholder
                })
                
                face_locations.append(face_location)
                face_encodings.append(face_encoding)
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectionResult(
                frame_number=frame_number,
                timestamp=datetime.now(),
                camera_id=camera_id,
                person_identities=person_identities,
                face_locations=face_locations,
                face_encodings=face_encodings,
                demographics=demographics_list,
                disguise_analysis=disguise_analysis,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing frame {frame_number}: {e}")
            return None
    
    def _identify_person(self, face_encoding: Any, face_image: Any,  # np.ndarray when available
                        camera_id: str) -> PersonIdentity:
        """Identify person using watchlist and cross-age detection"""
        if not CV2_AVAILABLE or face_recognition is None:
            # Return a default person identity if cv2 is not available
            self.person_counter += 1
            return PersonIdentity(
                person_id=f"person_{self.person_counter:06d}",
                person_type=PersonType.UNKNOWN,
                confidence_score=0.0
            )
        
        # Check against watchlist
        best_match_id = None
        best_similarity = 0.0
        person_type = PersonType.UNKNOWN
        
        for person_id, known_encoding in self.watchlist_manager.get_person_encodings().items():
            similarity = 1 - face_recognition.face_distance([known_encoding], face_encoding)[0]
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match_id = person_id
                # Determine person type
                for ptype, watchlist in self.watchlist_manager.watchlists.items():
                    if person_id in watchlist:
                        person_type = ptype
                        break
        
        # If no watchlist match, check against known persons
        if not best_match_id:
            for person_id, person_identity in self.known_persons.items():
                if person_identity.face_encoding is not None:
                    similarity = 1 - face_recognition.face_distance(
                        [person_identity.face_encoding], face_encoding)[0]
                    
                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_match_id = person_id
                        person_type = person_identity.person_type
        
        # Create or update person identity
        if best_match_id and best_match_id in self.known_persons:
            person_identity = self.known_persons[best_match_id]
            person_identity.last_seen = datetime.now()
            if camera_id not in person_identity.cameras_seen:
                person_identity.cameras_seen.append(camera_id)
        else:
            # New person
            self.person_counter += 1
            person_id = f"person_{self.person_counter:06d}"
            person_identity = PersonIdentity(
                person_id=person_id,
                person_type=person_type,
                face_encoding=face_encoding,
                confidence_score=best_similarity,
                last_seen=datetime.now(),
                cameras_seen=[camera_id],
                watchlist_status=best_match_id is not None
            )
            self.known_persons[person_id] = person_identity
        
        return person_identity
    
    def _get_demographics(self, face_image: Any,  # np.ndarray when available
                         person_identity: PersonIdentity) -> Dict:
        """Get demographics if privacy mode allows"""
        if self.privacy_mode:
            return {"privacy_mode": True}
        
        try:
            # Use FaceAi service for demographics
            demographics_result = self.faceai_service.analyze_demographics(face_image)
            if demographics_result.get("success") and demographics_result.get("results"):
                return demographics_result["results"][0]
        except Exception as e:
            logger.error(f"Error getting demographics: {e}")
        
        return {"error": "demographics_unavailable"}
    
    def add_to_watchlist(self, person_type: PersonType, name: str, 
                        face_image: Any, metadata: Dict = None) -> str:  # np.ndarray when available
        """Add person to watchlist"""
        if not CV2_AVAILABLE or face_recognition is None:
            raise ValueError("FaceAI dependencies not available")
        # Generate face encoding
        face_encodings = face_recognition.face_encodings(face_image)
        if not face_encodings:
            raise ValueError("No face found in image")
        
        face_encoding = face_encodings[0]
        person_id = f"{person_type.value}_{int(time.time())}"
        
        # Save to watchlist
        success = self.watchlist_manager.add_person(
            person_type, person_id, name, face_encoding, 
            metadata=metadata
        )
        
        if success:
            logger.info(f"Added {person_type.value} to watchlist: {name}")
            return person_id
        else:
            raise Exception("Failed to add person to watchlist")
    
    def get_person_tracking_summary(self) -> Dict:
        """Get summary of person tracking across cameras"""
        summary = {
            "total_persons": len(self.known_persons),
            "watchlist_persons": len(self.watchlist_manager.face_encodings_cache),
            "cameras_active": len(set(cam for person in self.known_persons.values() 
                                    for cam in person.cameras_seen)),
            "recent_activity": []
        }
        
        # Recent activity (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        for person in self.known_persons.values():
            if person.last_seen and person.last_seen > cutoff_time:
                summary["recent_activity"].append({
                    "person_id": person.person_id,
                    "person_type": person.person_type.value,
                    "last_seen": person.last_seen.isoformat(),
                    "cameras": person.cameras_seen
                })
        
        return summary

# Global agent instance
face_identity_agent = FaceIdentityAgent()

def get_face_identity_agent():
    """Get the global Face & Identity Agent instance"""
    return face_identity_agent

