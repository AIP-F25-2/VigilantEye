"""
CCTV Video Processing Controller for VIGILANTEye
Handles face detection, recognition, and watchlist management for CCTV feeds
"""

import json
import logging
from flask import Blueprint, request
from app import db
from app.services.face_identity_agent import get_face_identity_agent, PersonType
from app.models.faceai_models import FaceDetection, FaceEncoding
from app.utils.file_utils import (
    save_uploaded_file, validate_file_upload, 
    ALLOWED_VIDEO_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS,
    DEFAULT_FRAME_SKIP
)
from app.utils.response_utils import (
    success_response, error_response, handle_exception,
    HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_SERVICE_UNAVAILABLE
)
from app.utils.db_utils import save_model

logger = logging.getLogger(__name__)

# Create blueprint
cctv_bp = Blueprint("cctv", __name__, url_prefix="/api/cctv")

# Constants
CCTV_SOURCE_TYPE = "cctv_video"
DEFAULT_CAMERA_ID = "camera_001"
MODEL_VERSION = "face_identity_agent_v1.0"
HOURS_24 = 24
RECENT_DETECTIONS_LIMIT = 100

@cctv_bp.route("/status", methods=["GET"])
def get_agent_status():
    """Get Face & Identity Agent status"""
    try:
        agent = get_face_identity_agent()
        if not hasattr(agent, 'enabled') or not agent.enabled:
            return success_response({
                "agent_status": "disabled",
                "message": "FaceAI dependencies (cv2) not available. CCTV features disabled.",
                "tracking_summary": {
                    "total_persons": 0,
                    "watchlist_persons": 0,
                    "cameras_active": 0,
                    "recent_activity": []
                }
            })
        summary = agent.get_person_tracking_summary()
        
        return success_response({
            "agent_status": "active",
            "tracking_summary": summary,
            "privacy_mode": agent.privacy_mode,
            "similarity_threshold": agent.similarity_threshold
        })
    except Exception as e:
        return handle_exception(e, "Agent status", HTTP_INTERNAL_ERROR)

@cctv_bp.route("/process", methods=["POST"])
def process_cctv_video():
    """Process CCTV video for face detection and identification"""
    try:
        agent = get_face_identity_agent()
        if not hasattr(agent, 'enabled') or not agent.enabled:
            return error_response(
                "CCTV processing disabled: FaceAI dependencies (cv2) not available. Please install opencv-python, face-recognition, and numpy.",
                status_code=HTTP_SERVICE_UNAVAILABLE
            )
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'video')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded video
        video_path = save_uploaded_file(file, "cctv_videos", ALLOWED_VIDEO_EXTENSIONS)
        if not video_path:
            return error_response("Invalid video file type", status_code=HTTP_BAD_REQUEST)
        
        # Get parameters
        camera_id = request.form.get('camera_id', DEFAULT_CAMERA_ID)
        frame_skip = int(request.form.get('frame_skip', DEFAULT_FRAME_SKIP))
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
                    source_type=CCTV_SOURCE_TYPE,
                    source_path=video_path,
                    video_id=video_path,  # Using file path as video ID
                    frame_number=result.frame_number,
                    faces_detected=len(result.person_identities),
                    detection_results=[p.__dict__ for p in result.person_identities],
                    processing_time_ms=result.processing_time_ms,
                    model_version=MODEL_VERSION
                )
                db.session.add(face_detection)
                db.session.flush()  # Get the ID
                
                # Save face encodings (only if available - requires face_recognition)
                for i, (person_identity, face_encoding) in enumerate(zip(result.person_identities, result.face_encodings)):
                    if face_encoding is not None:
                        try:
                            # Convert numpy array to list if it's a numpy array
                            if hasattr(face_encoding, 'tolist'):
                                encoding_list = face_encoding.tolist()
                            else:
                                encoding_list = face_encoding if isinstance(face_encoding, list) else None
                            
                            if encoding_list is not None:
                                face_encoding_record = FaceEncoding(
                                    person_id=person_identity.person_id,
                                    face_detection_id=face_detection.id,
                                    source_path=video_path,
                                    face_encoding=encoding_list,
                                    bounding_box=result.face_locations[i],
                                    is_known_person=person_identity.watchlist_status,
                                    confidence_score=person_identity.confidence_score,
                                    model_version=MODEL_VERSION
                                )
                                db.session.add(face_encoding_record)
                        except Exception as e:
                            logger.warning(f"Failed to save face encoding for person {person_identity.person_id}: {e}")
                            # Continue processing even if encoding save fails
                
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
        
        return success_response({
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
        db.session.rollback()
        return handle_exception(e, "CCTV processing", HTTP_INTERNAL_ERROR)

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
                return error_response("Invalid person type", status_code=HTTP_BAD_REQUEST)
        else:
            watchlist = {}
            for ptype in PersonType:
                watchlist[ptype.value] = agent.watchlist_manager.watchlists[ptype]
        
        return success_response({
            "watchlist": watchlist,
            "total_encodings": len(agent.watchlist_manager.face_encodings_cache)
        })
        
    except Exception as e:
        return handle_exception(e, "Get watchlist", HTTP_INTERNAL_ERROR)

@cctv_bp.route("/watchlist", methods=["POST"])
def add_to_watchlist():
    """Add person to watchlist"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'image')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Get parameters
        person_type = request.form.get('person_type', 'unknown')
        name = request.form.get('name', '')
        metadata = request.form.get('metadata', '{}')
        
        try:
            person_type_enum = PersonType(person_type)
        except ValueError:
            return error_response("Invalid person type", status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded image
        image_path = save_uploaded_file(file, "watchlist_images", ALLOWED_IMAGE_EXTENSIONS)
        if not image_path:
            return error_response("Invalid image file type", status_code=HTTP_BAD_REQUEST)
        
        # Process image
        import cv2
        import face_recognition
        
        image = cv2.imread(image_path)
        if image is None:
            return error_response("Could not load image", status_code=HTTP_BAD_REQUEST)
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(image)
        if not face_encodings:
            return error_response("No face found in image", status_code=HTTP_BAD_REQUEST)
        
        # Add to watchlist
        agent = get_face_identity_agent()
        person_id = agent.add_to_watchlist(
            person_type_enum, 
            name, 
            image, 
            json.loads(metadata) if metadata else {}
        )
        
        return success_response({
            "person_id": person_id,
            "person_type": person_type,
            "name": name,
            "message": f"Added {name} to {person_type} watchlist"
        })
        
    except Exception as e:
        return handle_exception(e, "Add to watchlist", HTTP_INTERNAL_ERROR)

@cctv_bp.route("/watchlist/<person_id>", methods=["DELETE"])
def remove_from_watchlist(person_id):
    """Remove person from watchlist"""
    try:
        agent = get_face_identity_agent()
        success = agent.watchlist_manager.remove_person(person_id)
        
        if success:
            return success_response({
                "message": f"Removed person {person_id} from watchlist"
            })
        else:
            return error_response("Person not found in watchlist", 
                                status_code=HTTP_NOT_FOUND)
            
    except Exception as e:
        return handle_exception(e, "Remove from watchlist", HTTP_INTERNAL_ERROR)

@cctv_bp.route("/tracking", methods=["GET"])
def get_person_tracking():
    """Get person tracking information"""
    try:
        agent = get_face_identity_agent()
        summary = agent.get_person_tracking_summary()
        
        return success_response({
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
        return handle_exception(e, "Get tracking", HTTP_INTERNAL_ERROR)

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
        
        return success_response({
            "cameras": list(camera_activity.values()),
            "total_cameras": len(camera_activity)
        })
        
    except Exception as e:
        return handle_exception(e, "Get camera status", HTTP_INTERNAL_ERROR)

@cctv_bp.route("/alerts", methods=["GET"])
def get_watchlist_alerts():
    """Get recent watchlist alerts"""
    try:
        # Get recent detections with watchlist matches
        recent_detections = FaceDetection.query.filter(
            FaceDetection.created_at >= db.func.date_sub(
                db.func.now(), 
                db.text(f'INTERVAL {HOURS_24} HOUR')
            )
        ).order_by(FaceDetection.created_at.desc()).limit(RECENT_DETECTIONS_LIMIT).all()
        
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
        
        return success_response({
            "alerts": alerts,
            "total_alerts": len(alerts)
        })
        
    except Exception as e:
        return handle_exception(e, "Get alerts", HTTP_INTERNAL_ERROR)

