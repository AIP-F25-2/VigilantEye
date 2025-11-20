"""
AI Analytics API Controller for VigilantEye
Provides REST API endpoints for object detection, anomaly detection, behavior analysis, and smart alerts
"""

from flask import Blueprint, request
import time
import logging
from datetime import datetime
from app import db
from app.services.ai_analytics_service import get_ai_analytics_service
from app.models.ai_analytics_models import (
    ObjectDetection, AnomalyDetection, BehaviorAnalysis,
    CrowdDensityAnalysis, SmartAlert
)
from app.utils.file_utils import (
    save_uploaded_file, calculate_processing_time,
    validate_file_upload, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_FRAME_SKIP
)
from app.utils.response_utils import (
    success_response, error_response, handle_exception,
    paginated_response, HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE, HTTP_CREATED
)
from app.utils.db_utils import save_model

logger = logging.getLogger(__name__)

# Create blueprint
ai_analytics_bp = Blueprint("ai_analytics", __name__, url_prefix="/api/ai")

# Constants
MODEL_VERSION = "ai_analytics_v1.0"
DEFAULT_SOURCE_TYPE = "image"

@ai_analytics_bp.route("/status", methods=["GET"])
def get_status():
    """Get AI Analytics service status"""
    try:
        service = get_ai_analytics_service()
        status = service.get_service_status()
        return success_response({"status": status})
    except Exception as e:
        return handle_exception(e, "Status check", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/test-frame", methods=["POST"])
def test_frame():
    """Test endpoint to debug frame processing"""
    try:
        import cv2
        import numpy as np
        
        # Create a test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_frame, (100, 100), (200, 200), (0, 255, 0), 2)
        
        service = get_ai_analytics_service()
        logger.info(f"Service available: {service.is_available()}")
        logger.info(f"Service enabled: {service.enabled if hasattr(service, 'enabled') else 'N/A'}")
        
        result = service.process_frame(test_frame, 0, datetime.now())
        logger.info(f"Test result: {result}")
        
        return success_response({
            "test_result": result,
            "service_available": service.is_available(),
            "service_enabled": service.enabled if hasattr(service, 'enabled') else False
        })
    except Exception as e:
        logger.error(f"Test frame error: {e}", exc_info=True)
        return error_response(f"Test failed: {str(e)}", status_code=HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/detect-objects", methods=["POST"])
def detect_objects():
    """Detect objects in an uploaded image or video frame"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'image')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "ai_analytics", ALLOWED_IMAGE_EXTENSIONS)
        if not filepath:
            return error_response("Invalid file type", status_code=HTTP_BAD_REQUEST)
        
        # Get parameters
        source_type = request.form.get('source_type', DEFAULT_SOURCE_TYPE)
        video_id = request.form.get('video_id')
        frame_number = request.form.get('frame_number', type=int)
        camera_id = request.form.get('camera_id')
        min_confidence = float(request.form.get('min_confidence', 0.3))
        
        # Get service
        service = get_ai_analytics_service()
        if not service.is_available():
            return error_response("AI Analytics service not available",
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process image
        import cv2
        image = cv2.imread(filepath)
        if image is None:
            return error_response("Could not load image", status_code=HTTP_BAD_REQUEST)
        
        start_time = time.time()
        detected_objects = service.object_detector.detect_objects(image, min_confidence)
        processing_time = calculate_processing_time(start_time)
        
        # Save to database
        detection = ObjectDetection(
            source_type=source_type,
            source_path=filepath,
            video_id=video_id,
            frame_number=frame_number,
            camera_id=camera_id,
            objects_detected=len(detected_objects),
            detection_results=[
                {
                    "type": obj.object_type,
                    "confidence": obj.confidence,
                    "bounding_box": obj.bounding_box,
                    "center": obj.center,
                    "area": obj.area
                } for obj in detected_objects
            ],
            processing_time_ms=processing_time,
            model_version=MODEL_VERSION,
            confidence_threshold=min_confidence
        )
        success, _ = save_model(detection)
        if success:
            detection_id = detection.id
        else:
            detection_id = None
        
        return success_response({
            "detection_id": detection_id,
            "objects_detected": len(detected_objects),
            "objects": [
                {
                    "type": obj.object_type,
                    "confidence": obj.confidence,
                    "bounding_box": obj.bounding_box,
                    "center": obj.center,
                    "area": obj.area
                } for obj in detected_objects
            ],
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        return handle_exception(e, "Object detection", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/analyze-frame", methods=["POST"])
def analyze_frame():
    """Comprehensive AI analysis of a single frame"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'image')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "ai_analytics", ALLOWED_IMAGE_EXTENSIONS)
        if not filepath:
            return error_response("Invalid file type", status_code=HTTP_BAD_REQUEST)
        
        # Get parameters
        source_type = request.form.get('source_type', DEFAULT_SOURCE_TYPE)
        video_id = request.form.get('video_id')
        frame_number = request.form.get('frame_number', type=int) or 0
        camera_id = request.form.get('camera_id')
        
        # Get service
        service = get_ai_analytics_service()
        if not service.is_available():
            return error_response("AI Analytics service not available",
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process frame
        try:
            import cv2
            frame = cv2.imread(filepath)
            if frame is None:
                return error_response("Could not load image. Please ensure the file is a valid image format.", status_code=HTTP_BAD_REQUEST)
        except ImportError:
            return error_response("OpenCV (cv2) is not available. Please install opencv-python.", status_code=HTTP_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return error_response(f"Error loading image: {str(e)}", status_code=HTTP_BAD_REQUEST)
        
        start_time = time.time()
        try:
            result = service.process_frame(frame, frame_number, datetime.now())
            logger.info(f"Service process_frame returned: success={result.get('success')}, error={result.get('error')}")
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            return error_response(f"Error processing frame: {str(e)}", status_code=HTTP_INTERNAL_ERROR)
        
        processing_time = calculate_processing_time(start_time)
        
        # Check for errors first
        if result.get("error"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Service returned error: {error_msg}, full result: {result}")
            return error_response(f"Analysis failed: {error_msg}", status_code=HTTP_INTERNAL_ERROR)
        
        # Check if success is explicitly False or missing
        if result.get("success") is False or (result.get("success") is not True and result.get("error")):
            error_msg = result.get("error", "Service returned unsuccessful result")
            logger.error(f"Service returned unsuccessful result. Error: {error_msg}, Full result: {result}")
            return error_response(f"Analysis failed: {error_msg}", status_code=HTTP_INTERNAL_ERROR)
        
        # If success is not True and no error, log warning but try to continue
        if result.get("success") is not True:
            logger.warning(f"Service result missing 'success: True', but no error found. Result keys: {list(result.keys())}")
            # If we have the expected data structure, continue anyway
            if "objects_detected" in result or "anomalies" in result or "behaviors" in result:
                logger.info("Result has expected data structure, continuing despite missing success flag")
            else:
                logger.error("Result missing both success flag and expected data structure")
                return error_response("Analysis failed: Invalid response structure from service", status_code=HTTP_INTERNAL_ERROR)
        
        # Save results to database (non-blocking - don't fail if DB save fails)
        saved_ids = {}
        db_errors = []
        
        try:
            # Save object detection
            if result.get("objects"):
                try:
                    obj_detection = ObjectDetection(
                        source_type=source_type,
                        source_path=filepath,
                        video_id=video_id,
                        frame_number=frame_number,
                        camera_id=camera_id,
                        objects_detected=result.get("objects_detected", 0),
                        detection_results=result.get("objects"),
                        processing_time_ms=processing_time,
                        model_version=MODEL_VERSION
                    )
                    success, error = save_model(obj_detection)
                    if success:
                        saved_ids["object_detection_id"] = obj_detection.id
                    else:
                        db_errors.append(f"ObjectDetection save failed: {error}")
                except Exception as e:
                    logger.warning(f"Failed to save object detection: {e}")
                    db_errors.append(f"ObjectDetection save error: {str(e)}")
            
            # Save anomalies
            if result.get("anomalies"):
                for anomaly_data in result.get("anomalies", []):
                    try:
                        anomaly = AnomalyDetection(
                            source_type=source_type,
                            source_path=filepath,
                            video_id=video_id,
                            frame_number=frame_number,
                            camera_id=camera_id,
                            anomaly_type=anomaly_data.get("type"),
                            confidence=anomaly_data.get("confidence"),
                            location=anomaly_data.get("location"),
                            description=anomaly_data.get("description"),
                            metadata_json=anomaly_data.get("metadata"),
                            processing_time_ms=processing_time,
                            model_version=MODEL_VERSION
                        )
                        save_model(anomaly)  # Don't check result - non-blocking
                    except Exception as e:
                        logger.warning(f"Failed to save anomaly: {e}")
            
            # Save behaviors
            if result.get("behaviors"):
                for behavior_data in result.get("behaviors", []):
                    try:
                        behavior = BehaviorAnalysis(
                            source_type=source_type,
                            source_path=filepath,
                            video_id=video_id,
                            frame_number=frame_number,
                            camera_id=camera_id,
                            behavior_type=behavior_data.get("type"),
                            confidence=behavior_data.get("confidence"),
                            duration_seconds=behavior_data.get("duration_seconds"),
                            location=behavior_data.get("location"),
                            metadata_json=behavior_data.get("metadata"),
                            processing_time_ms=processing_time,
                            model_version=MODEL_VERSION
                        )
                        save_model(behavior)  # Don't check result - non-blocking
                    except Exception as e:
                        logger.warning(f"Failed to save behavior: {e}")
            
            # Save crowd density
            if result.get("crowd_density"):
                try:
                    crowd_data = result.get("crowd_density", {})
                    crowd = CrowdDensityAnalysis(
                        source_type=source_type,
                        source_path=filepath,
                        video_id=video_id,
                        frame_number=frame_number,
                        camera_id=camera_id,
                        density_level=crowd_data.get("density_level"),
                        person_count=crowd_data.get("person_count", 0),
                        density_percentage=crowd_data.get("density_percentage", 0.0),
                        high_density_areas=crowd_data.get("areas", []),
                        processing_time_ms=processing_time,
                        model_version=MODEL_VERSION
                    )
                    success, error = save_model(crowd)
                    if success:
                        saved_ids["crowd_density_id"] = crowd.id
                    else:
                        db_errors.append(f"CrowdDensityAnalysis save failed: {error}")
                except Exception as e:
                    logger.warning(f"Failed to save crowd density: {e}")
                    db_errors.append(f"CrowdDensityAnalysis save error: {str(e)}")
        except Exception as e:
            logger.warning(f"Database save operations failed: {e}", exc_info=True)
            db_errors.append(f"Database operations error: {str(e)}")
        
        # Add saved IDs and processing time to result
        result["saved_ids"] = saved_ids
        result["processing_time_ms"] = processing_time
        if db_errors:
            result["db_warnings"] = db_errors  # Add warnings but don't fail
        
        return success_response(result)
        
    except Exception as e:
        return handle_exception(e, "Frame analysis", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/analyze-video", methods=["POST"])
def analyze_video():
    """Analyze entire video for AI insights"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'video')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded video
        video_path = save_uploaded_file(file, "ai_analytics", ALLOWED_VIDEO_EXTENSIONS)
        if not video_path:
            return error_response("Invalid video file type", status_code=HTTP_BAD_REQUEST)
        
        # Get parameters
        camera_id = request.form.get('camera_id')
        frame_skip = int(request.form.get('frame_skip', DEFAULT_FRAME_SKIP))
        
        # Get service
        service = get_ai_analytics_service()
        if not service.is_available():
            return error_response("AI Analytics service not available",
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process video
        start_time = time.time()
        try:
            result = service.process_video(video_path, frame_skip)
        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            return error_response(f"Error processing video: {str(e)}", status_code=HTTP_INTERNAL_ERROR)
        
        processing_time = calculate_processing_time(start_time)
        
        if result.get("error"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Service returned error: {error_msg}")
            return error_response(f"Video analysis failed: {error_msg}", status_code=HTTP_INTERNAL_ERROR)
        
        if not result.get("success"):
            logger.error(f"Service returned unsuccessful result: {result}")
            return error_response("Video analysis failed: Service returned unsuccessful result", status_code=HTTP_INTERNAL_ERROR)
        
        result["processing_time_ms"] = processing_time
        result["video_path"] = video_path
        
        return success_response(result)
        
    except Exception as e:
        return handle_exception(e, "Video analysis", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/anomalies", methods=["GET"])
def get_anomalies():
    """Get anomaly detection history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        anomaly_type = request.args.get('type')
        camera_id = request.args.get('camera_id')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = AnomalyDetection.query
        
        if anomaly_type:
            query = query.filter_by(anomaly_type=anomaly_type)
        if camera_id:
            query = query.filter_by(camera_id=camera_id)
        if unread_only:
            query = query.filter_by(is_alert=True, alert_sent=False)
        
        anomalies = query.order_by(AnomalyDetection.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return paginated_response(
            [anomaly.to_dict() for anomaly in anomalies.items],
            page, per_page, anomalies.total, anomalies.pages,
            data_key="anomalies"
        )
        
    except Exception as e:
        return handle_exception(e, "Get anomalies", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/behaviors", methods=["GET"])
def get_behaviors():
    """Get behavior analysis history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        behavior_type = request.args.get('type')
        camera_id = request.args.get('camera_id')
        
        query = BehaviorAnalysis.query
        
        if behavior_type:
            query = query.filter_by(behavior_type=behavior_type)
        if camera_id:
            query = query.filter_by(camera_id=camera_id)
        
        behaviors = query.order_by(BehaviorAnalysis.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return paginated_response(
            [behavior.to_dict() for behavior in behaviors.items],
            page, per_page, behaviors.total, behaviors.pages,
            data_key="behaviors"
        )
        
    except Exception as e:
        return handle_exception(e, "Get behaviors", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/crowd-density", methods=["GET"])
def get_crowd_density():
    """Get crowd density analysis history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        camera_id = request.args.get('camera_id')
        density_level = request.args.get('density_level')
        
        query = CrowdDensityAnalysis.query
        
        if camera_id:
            query = query.filter_by(camera_id=camera_id)
        if density_level:
            query = query.filter_by(density_level=density_level)
        
        analyses = query.order_by(CrowdDensityAnalysis.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return paginated_response(
            [analysis.to_dict() for analysis in analyses.items],
            page, per_page, analyses.total, analyses.pages,
            data_key="analyses"
        )
        
    except Exception as e:
        return handle_exception(e, "Get crowd density", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/alerts", methods=["GET"])
def get_smart_alerts():
    """Get smart alerts"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        alert_type = request.args.get('type')
        severity = request.args.get('severity')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = SmartAlert.query
        
        if alert_type:
            query = query.filter_by(alert_type=alert_type)
        if severity:
            query = query.filter_by(severity=severity)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        alerts = query.order_by(SmartAlert.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return paginated_response(
            [alert.to_dict() for alert in alerts.items],
            page, per_page, alerts.total, alerts.pages,
            data_key="alerts"
        )
        
    except Exception as e:
        return handle_exception(e, "Get alerts", HTTP_INTERNAL_ERROR)

@ai_analytics_bp.route("/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id):
    """Acknowledge a smart alert"""
    try:
        alert = SmartAlert.query.get_or_404(alert_id)
        data = request.get_json() or {}
        
        alert.is_read = True
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = data.get('acknowledged_by', 'system')
        
        db.session.commit()
        
        return success_response({"alert": alert.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return handle_exception(e, "Acknowledge alert", HTTP_INTERNAL_ERROR)

