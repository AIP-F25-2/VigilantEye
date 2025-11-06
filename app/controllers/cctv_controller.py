"""
CCTV Video Processing Controller for VIGILANTEye
Handles face detection, recognition, and watchlist management for CCTV feeds
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import time
import logging
from pathlib import Path
from app import db
from app.services.face_identity_agent import get_face_identity_agent, PersonType
from app.models.faceai_models import FaceDetection, FaceEncoding

logger = logging.getLogger(__name__)

# Create blueprint
cctv_bp = Blueprint("cctv", __name__, url_prefix="/api/cctv")

# Allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}

def allowed_video_file(filename):
    """Check if video file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def save_uploaded_video(file, subfolder="cctv_videos"):
    """Save uploaded video file and return path"""
    if file and allowed_video_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        
        upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), subfolder)
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        return filepath
    return None

@cctv_bp.route("/status", methods=["GET"])
def get_agent_status():
    """Get Face & Identity Agent status"""
    try:
        agent = get_face_identity_agent()
        summary = agent.get_person_tracking_summary()
        
        return jsonify({
            "success": True,
            "agent_status": "active",
            "tracking_summary": summary,
            "privacy_mode": agent.privacy_mode,
            "similarity_threshold": agent.similarity_threshold
        })
    except Exception as e:
        logger.error(f"Agent status error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/process", methods=["POST"])
def process_cctv_video():
    """Process CCTV video for face detection and identification"""
    try:
        if 'video' not in request.files:
            return jsonify({"error": "No video file provided"}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded video
        video_path = save_uploaded_video(file)
        if not video_path:
            return jsonify({"error": "Invalid video file type"}), 400
        
        # Get parameters
        camera_id = request.form.get('camera_id', 'camera_001')
        frame_skip = int(request.form.get('frame_skip', 30))
        privacy_mode = request.form.get('privacy_mode', 'false').lower() == 'true'
        
        # Get agent and process video
        agent = get_face_identity_agent()
        agent.privacy_mode = privacy_mode
        
        results = agent.process_cctv_video(video_path, camera_id, frame_skip)
        
        # Save results to database
        saved_detections = []
        for result in results:
            try:
                # Save face detection
                face_detection = FaceDetection(
                    source_type='cctv_video',
                    source_path=video_path,
                    video_id=video_path,  # Using file path as video ID
                    frame_number=result.frame_number,
                    faces_detected=len(result.person_identities),
                    detection_results=[p.__dict__ for p in result.person_identities],
                    processing_time_ms=result.processing_time_ms,
                    model_version="face_identity_agent_v1.0"
                )
                db.session.add(face_detection)
                db.session.flush()  # Get the ID
                
                # Save face encodings
                for i, (person_identity, face_encoding) in enumerate(zip(result.person_identities, result.face_encodings)):
                    face_encoding_record = FaceEncoding(
                        person_id=person_identity.person_id,
                        face_detection_id=face_detection.id,
                        source_path=video_path,
                        face_encoding=face_encoding.tolist(),  # Convert numpy array to list
                        bounding_box=result.face_locations[i],
                        is_known_person=person_identity.watchlist_status,
                        confidence_score=person_identity.confidence_score,
                        model_version="face_identity_agent_v1.0"
                    )
                    db.session.add(face_encoding_record)
                
                saved_detections.append({
                    "detection_id": face_detection.id,
                    "frame_number": result.frame_number,
                    "timestamp": result.timestamp.isoformat(),
                    "faces_detected": len(result.person_identities),
                    "person_identities": [
                        {
                            "person_id": p.person_id,
                            "person_type": p.person_type.value,
                            "confidence_score": p.confidence_score,
                            "watchlist_status": p.watchlist_status,
                            "cameras_seen": p.cameras_seen
                        } for p in result.person_identities
                    ]
                })
                
            except Exception as e:
                logger.error(f"Error saving detection result: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "video_path": video_path,
            "camera_id": camera_id,
            "frames_processed": len(results),
            "detections_saved": len(saved_detections),
            "detections": saved_detections,
            "processing_summary": {
                "total_faces": sum(len(r.person_identities) for r in results),
                "unique_persons": len(set(p.person_id for r in results for p in r.person_identities)),
                "watchlist_matches": sum(1 for r in results for p in r.person_identities if p.watchlist_status)
            }
        })
        
    except Exception as e:
        logger.error(f"CCTV processing error: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    """Get watchlist members"""
    try:
        agent = get_face_identity_agent()
        person_type = request.args.get('type')
        
        if person_type:
            try:
                person_type_enum = PersonType(person_type)
                watchlist = agent.watchlist_manager.watchlists[person_type_enum]
            except ValueError:
                return jsonify({"error": "Invalid person type"}), 400
        else:
            watchlist = {}
            for ptype in PersonType:
                watchlist[ptype.value] = agent.watchlist_manager.watchlists[ptype]
        
        return jsonify({
            "success": True,
            "watchlist": watchlist,
            "total_encodings": len(agent.watchlist_manager.face_encodings_cache)
        })
        
    except Exception as e:
        logger.error(f"Get watchlist error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    """Add person to watchlist"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Get parameters
        person_type = request.form.get('person_type', 'unknown')
        name = request.form.get('name', '')
        metadata = request.form.get('metadata', '{}')
        
        try:
            person_type_enum = PersonType(person_type)
        except ValueError:
            return jsonify({"error": "Invalid person type"}), 400
        
        # Save uploaded image
        image_path = save_uploaded_video(file, "watchlist_images")
        if not image_path:
            return jsonify({"error": "Invalid image file type"}), 400
        
        # Process image
        import cv2
        import numpy as np
        import face_recognition
        
        image = cv2.imread(image_path)
        if image is None:
            return jsonify({"error": "Could not load image"}), 400
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(image)
        if not face_encodings:
            return jsonify({"error": "No face found in image"}), 400
        
        face_encoding = face_encodings[0]
        
        # Add to watchlist
        agent = get_face_identity_agent()
        person_id = agent.add_to_watchlist(
            person_type_enum, 
            name, 
            image, 
            json.loads(metadata) if metadata else {}
        )
        
        return jsonify({
            "success": True,
            "person_id": person_id,
            "person_type": person_type,
            "name": name,
            "message": f"Added {name} to {person_type} watchlist"
        })
        
    except Exception as e:
        logger.error(f"Add to watchlist error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/watchlist/<person_id>", methods=["DELETE"])
def remove_from_watchlist(person_id):
    """Remove person from watchlist"""
    try:
        agent = get_face_identity_agent()
        success = agent.watchlist_manager.remove_person(person_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Removed person {person_id} from watchlist"
            })
        else:
            return jsonify({"error": "Person not found in watchlist"}), 404
            
    except Exception as e:
        logger.error(f"Remove from watchlist error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/tracking", methods=["GET"])
def get_person_tracking():
    """Get person tracking information"""
    try:
        agent = get_face_identity_agent()
        summary = agent.get_person_tracking_summary()
        
        return jsonify({
            "success": True,
            "tracking_summary": summary,
            "known_persons": {
                person_id: {
                    "person_type": person.person_type.value,
                    "confidence_score": person.confidence_score,
                    "last_seen": person.last_seen.isoformat() if person.last_seen else None,
                    "cameras_seen": person.cameras_seen,
                    "watchlist_status": person.watchlist_status
                } for person_id, person in agent.known_persons.items()
            }
        })
        
    except Exception as e:
        logger.error(f"Get tracking error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/cameras", methods=["GET"])
def get_camera_status():
    """Get camera status and activity"""
    try:
        agent = get_face_identity_agent()
        
        # Get camera activity from tracking
        camera_activity = {}
        for person in agent.known_persons.values():
            for camera_id in person.cameras_seen:
                if camera_id not in camera_activity:
                    camera_activity[camera_id] = {
                        "camera_id": camera_id,
                        "persons_detected": 0,
                        "last_activity": None,
                        "watchlist_alerts": 0
                    }
                
                camera_activity[camera_id]["persons_detected"] += 1
                if person.last_seen and (not camera_activity[camera_id]["last_activity"] or 
                                       person.last_seen > camera_activity[camera_id]["last_activity"]):
                    camera_activity[camera_id]["last_activity"] = person.last_seen.isoformat()
                
                if person.watchlist_status:
                    camera_activity[camera_id]["watchlist_alerts"] += 1
        
        return jsonify({
            "success": True,
            "cameras": list(camera_activity.values()),
            "total_cameras": len(camera_activity)
        })
        
    except Exception as e:
        logger.error(f"Get camera status error: {e}")
        return jsonify({"error": str(e)}), 500

@cctv_bp.route("/alerts", methods=["GET"])
def get_watchlist_alerts():
    """Get recent watchlist alerts"""
    try:
        # Get recent detections with watchlist matches
        recent_detections = FaceDetection.query.filter(
            FaceDetection.created_at >= db.func.date_sub(db.func.now(), db.text('INTERVAL 24 HOUR'))
        ).order_by(FaceDetection.created_at.desc()).limit(100).all()
        
        alerts = []
        for detection in recent_detections:
            if detection.detection_results:
                for person_data in detection.detection_results:
                    if isinstance(person_data, dict) and person_data.get('watchlist_status'):
                        alerts.append({
                            "detection_id": detection.id,
                            "timestamp": detection.created_at.isoformat(),
                            "camera_id": detection.source_path,
                            "person_id": person_data.get('person_id'),
                            "person_type": person_data.get('person_type'),
                            "confidence_score": person_data.get('confidence_score'),
                            "frame_number": detection.frame_number
                        })
        
        return jsonify({
            "success": True,
            "alerts": alerts,
            "total_alerts": len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        return jsonify({"error": str(e)}), 500

