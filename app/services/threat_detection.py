import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import threading
import time
import random

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    MOTION = "motion"
    INTRUSION = "intrusion"
    WEAPON = "weapon"
    FIRE = "fire"
    VIOLENCE = "violence"
    SUSPICIOUS_OBJECT = "suspicious_object"
    CROWD_GATHERING = "crowd_gathering"
    VEHICLE_ANOMALY = "vehicle_anomaly"

class ThreatDetectionService:
    """Advanced threat detection service for security monitoring"""
    
    def __init__(self):
        self.active_detections = {}
        self.threat_history = []
        self.alert_callbacks = []
        self.is_running = False
        self.detection_threads = {}
        
        # Detection parameters
        self.motion_threshold = 5000
        self.weapon_confidence = 0.7
        self.fire_confidence = 0.8
        self.crowd_threshold = 10
        
    def start_detection(self, camera_id: str, stream_url: str):
        """Start threat detection for a specific camera"""
        if camera_id in self.detection_threads:
            return False
            
        thread = threading.Thread(
            target=self._detection_loop,
            args=(camera_id, stream_url),
            daemon=True
        )
        thread.start()
        self.detection_threads[camera_id] = thread
        self.is_running = True
        return True
    
    def stop_detection(self, camera_id: str):
        """Stop threat detection for a specific camera"""
        if camera_id in self.detection_threads:
            self.active_detections.pop(camera_id, None)
            # Note: Thread will stop when is_running becomes False
    
    def _detection_loop(self, camera_id: str, stream_url: str):
        """Main detection loop for continuous monitoring (simulated)"""
        try:
            frame_count = 0
            last_motion_time = None
            
            while self.is_running and camera_id in self.detection_threads:
                frame_count += 1
                
                # Simulate frame analysis
                threats = self._analyze_frame_simulated(camera_id, frame_count)
                
                # Process detected threats
                for threat in threats:
                    self._process_threat(camera_id, threat, None)
                
                # Simulate motion detection
                if random.random() < 0.1:  # 10% chance of motion
                    last_motion_time = datetime.now()
                    self._create_threat_alert(
                        camera_id=camera_id,
                        threat_type=ThreatType.MOTION,
                        threat_level=ThreatLevel.LOW,
                        confidence=0.8,
                        description="Motion detected in restricted area",
                        frame=None
                    )
                
                # Check for prolonged inactivity (potential tampering)
                if last_motion_time and (datetime.now() - last_motion_time).seconds > 300:
                    self._create_threat_alert(
                        camera_id=camera_id,
                        threat_type=ThreatType.SUSPICIOUS_OBJECT,
                        threat_level=ThreatLevel.MEDIUM,
                        confidence=0.6,
                        description="Camera may be tampered with - no motion for 5 minutes",
                        frame=None
                    )
                    last_motion_time = None
                
                time.sleep(2)  # Check every 2 seconds
                
        except Exception as e:
            print(f"Error in detection loop for camera {camera_id}: {e}")
    
    def _analyze_frame_simulated(self, camera_id: str, frame_count: int) -> List[Dict]:
        """Simulate frame analysis for various threats"""
        threats = []
        
        # Simulate weapon detection
        if frame_count % 50 == 0 and random.random() < 0.02:  # 2% chance every 50 frames
            threats.append({
                'type': ThreatType.WEAPON,
                'level': ThreatLevel.CRITICAL,
                'confidence': 0.85,
                'description': 'Weapon detected in frame',
                'bbox': (100, 100, 200, 200)
            })
        
        # Simulate fire detection
        if frame_count % 75 == 0 and random.random() < 0.01:  # 1% chance every 75 frames
            threats.append({
                'type': ThreatType.FIRE,
                'level': ThreatLevel.HIGH,
                'confidence': 0.9,
                'description': 'Fire detected in surveillance area',
                'bbox': (150, 150, 250, 250)
            })
        
        # Simulate crowd gathering detection
        if frame_count % 100 == 0 and random.random() < 0.03:  # 3% chance every 100 frames
            threats.append({
                'type': ThreatType.CROWD_GATHERING,
                'level': ThreatLevel.MEDIUM,
                'confidence': 0.7,
                'description': 'Unusual crowd gathering detected',
                'bbox': (0, 0, 640, 480)
            })
        
        # Simulate intrusion detection
        if frame_count % 30 == 0 and random.random() < 0.05:  # 5% chance every 30 frames
            threats.append({
                'type': ThreatType.INTRUSION,
                'level': ThreatLevel.HIGH,
                'confidence': 0.8,
                'description': 'Unauthorized person detected in restricted area',
                'bbox': (200, 200, 300, 300)
            })
        
        return threats
    
    def _detect_motion_simulated(self) -> bool:
        """Simulate motion detection"""
        return random.random() < 0.1  # 10% chance of motion
    
    def _process_threat(self, camera_id: str, threat: Dict, frame):
        """Process detected threat and create alert"""
        self._create_threat_alert(
            camera_id=camera_id,
            threat_type=threat['type'],
            threat_level=threat['level'],
            confidence=threat['confidence'],
            description=threat['description'],
            frame=frame,
            bbox=threat.get('bbox')
        )
    
    def _create_threat_alert(self, camera_id: str, threat_type: ThreatType, 
                           threat_level: ThreatLevel, confidence: float, 
                           description: str, frame, bbox: Optional[Tuple] = None):
        """Create and process threat alert"""
        alert = {
            'id': f"alert_{camera_id}_{int(time.time())}",
            'camera_id': camera_id,
            'threat_type': threat_type.value,
            'threat_level': threat_level.value,
            'confidence': confidence,
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'bbox': bbox,
            'acknowledged': False,
            'resolved': False
        }
        
        # Store in threat history
        self.threat_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.threat_history) > 1000:
            self.threat_history = self.threat_history[-1000:]
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
        
        print(f"🚨 THREAT ALERT: {threat_level.value.upper()} - {description} (Camera: {camera_id})")
    
    def add_alert_callback(self, callback):
        """Add callback function for threat alerts"""
        self.alert_callbacks.append(callback)
    
    def get_active_threats(self) -> List[Dict]:
        """Get currently active threats"""
        return [alert for alert in self.threat_history 
                if not alert.get('resolved', False) and 
                (datetime.now() - datetime.fromisoformat(alert['timestamp'])).seconds < 3600]
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge a threat alert"""
        for alert in self.threat_history:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                break
    
    def resolve_alert(self, alert_id: str):
        """Mark a threat alert as resolved"""
        for alert in self.threat_history:
            if alert['id'] == alert_id:
                alert['resolved'] = True
                break
    
    def get_threat_statistics(self) -> Dict:
        """Get threat detection statistics"""
        now = datetime.now()
        last_24h = [alert for alert in self.threat_history 
                   if (now - datetime.fromisoformat(alert['timestamp'])).days < 1]
        
        stats = {
            'total_alerts': len(self.threat_history),
            'active_alerts': len(self.get_active_threats()),
            'alerts_24h': len(last_24h),
            'critical_alerts': len([a for a in last_24h if a['threat_level'] == 'critical']),
            'high_alerts': len([a for a in last_24h if a['threat_level'] == 'high']),
            'threat_types': {}
        }
        
        # Count by threat type
        for alert in last_24h:
            threat_type = alert['threat_type']
            stats['threat_types'][threat_type] = stats['threat_types'].get(threat_type, 0) + 1
        
        return stats

# Global threat detection service instance
threat_detector = ThreatDetectionService()
