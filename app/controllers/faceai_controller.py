"""
FaceAi API Controller for VIGILANTEye
Provides REST API endpoints for face detection, demographics, and ambiguity analysis
"""

from flask import Blueprint, request
import time
import logging
from app import db
from app.services.faceai_service import get_faceai_service
from app.models.faceai_models import (
    FaceDetection, DemographicsAnalysis, AmbiguityAnalysis, 
    FaceEncoding, FaceAiConfiguration
)
from app.utils.file_utils import (
    save_uploaded_file, calculate_processing_time, 
    validate_file_upload, ALLOWED_IMAGE_EXTENSIONS
)
from app.utils.response_utils import (
    success_response, error_response, handle_exception,
    paginated_response, HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE, HTTP_CREATED
)
from app.utils.db_utils import save_model

logger = logging.getLogger(__name__)

# Create blueprint
faceai_bp = Blueprint("faceai", __name__, url_prefix="/api/faceai")

# Constants
MODEL_VERSION = "1.0"
DEFAULT_SOURCE_TYPE = "image"
FACEAI_SERVICE_UNAVAILABLE_MSG = "FaceAi service not available"

@faceai_bp.route("/status", methods=["GET"])
def get_status():
    """Get FaceAi service status"""
    try:
        service = get_faceai_service()
        status = service.get_service_status()
        return success_response({"status": status})
    except Exception as e:
        return handle_exception(e, "Status check", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/detect", methods=["POST"])
def detect_faces():
    """Detect and recognize faces in an uploaded image"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'image')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "faceai", ALLOWED_IMAGE_EXTENSIONS)
        if not filepath:
            return error_response("Invalid file type", status_code=HTTP_BAD_REQUEST)
        
        # Get additional parameters
        source_type = request.form.get('source_type', DEFAULT_SOURCE_TYPE)
        video_id = request.form.get('video_id')
        frame_number = request.form.get('frame_number', type=int)
        show_result = request.form.get('show_result', 'false').lower() == 'true'
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return error_response(FACEAI_SERVICE_UNAVAILABLE_MSG, 
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process image
        start_time = time.time()
        result = service.detect_faces(filepath, show_result=show_result)
        processing_time = calculate_processing_time(start_time)
        
        if result.get("error"):
            return error_response(result.get("error"), status_code=HTTP_INTERNAL_ERROR)
        
        # Save to database
        face_detection = FaceDetection(
            source_type=source_type,
            source_path=filepath,
            video_id=video_id,
            frame_number=frame_number,
            faces_detected=result.get("faces_detected", 0),
            detection_results=result.get("results"),
            processing_time_ms=processing_time,
            model_version=MODEL_VERSION
        )
        success, _ = save_model(face_detection)
        if success:
            result["detection_id"] = face_detection.id
        
        return success_response({
            "detection_id": result.get("detection_id"),
            "faces_detected": result.get("faces_detected", 0),
            "results": result.get("results", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        return handle_exception(e, "Face detection", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/demographics", methods=["POST"])
def analyze_demographics():
    """Analyze age and gender demographics of faces in an image"""
    try:
        # Validate file upload
        file, error_msg = validate_file_upload(request.files, 'image')
        if error_msg:
            return error_response(error_msg, status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "faceai", ALLOWED_IMAGE_EXTENSIONS)
        if not filepath:
            return error_response("Invalid file type", status_code=HTTP_BAD_REQUEST)
        
        # Get additional parameters
        source_type = request.form.get('source_type', DEFAULT_SOURCE_TYPE)
        face_detection_id = request.form.get('face_detection_id')
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return error_response(FACEAI_SERVICE_UNAVAILABLE_MSG, 
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process image
        start_time = time.time()
        result = service.analyze_demographics(filepath)
        processing_time = calculate_processing_time(start_time)
        
        if result.get("error"):
            # Check if it's a service unavailable error (demographics not available)
            if "not available" in result.get("error", "").lower():
                # Return error with additional info if available
                error_data = {
                    "message": result.get("error", "Demographics analyzer not available"),
                    "available_features": result.get("available_features", {}),
                    "suggestion": result.get("suggestion", "")
                }
                return error_response(
                    error_data,
                    status_code=HTTP_SERVICE_UNAVAILABLE
                )
            return error_response(result.get("error"), status_code=HTTP_INTERNAL_ERROR)
        
        # Save to database (only if analysis was successful)
        demographics_analysis = DemographicsAnalysis(
            face_detection_id=face_detection_id,
            source_type=source_type,
            source_path=filepath,
            faces_analyzed=result.get("faces_analyzed", 0),
            analysis_results=result.get("results"),
            processing_time_ms=processing_time,
            model_version=MODEL_VERSION
        )
        success, _ = save_model(demographics_analysis)
        if success:
            result["analysis_id"] = demographics_analysis.id
        
        return success_response({
            "analysis_id": result.get("analysis_id"),
            "faces_analyzed": result.get("faces_analyzed", 0),
            "results": result.get("results", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        return handle_exception(e, "Demographics analysis", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/ambiguity", methods=["POST"])
def check_ambiguity():
    """Check if two images show the same person (ambiguity detection)"""
    try:
        # Validate file uploads
        file1, error_msg1 = validate_file_upload(request.files, 'image1')
        file2, error_msg2 = validate_file_upload(request.files, 'image2')
        
        if error_msg1 or error_msg2:
            return error_response("Two image files required (image1 and image2)", 
                                status_code=HTTP_BAD_REQUEST)
        
        # Save uploaded files
        filepath1 = save_uploaded_file(file1, "faceai", ALLOWED_IMAGE_EXTENSIONS)
        filepath2 = save_uploaded_file(file2, "faceai", ALLOWED_IMAGE_EXTENSIONS)
        
        if not filepath1 or not filepath2:
            return error_response("Invalid file types", status_code=HTTP_BAD_REQUEST)
        
        # Get additional parameters
        source_type = request.form.get('source_type', 'comparison')
        show_result = request.form.get('show_result', 'false').lower() == 'true'
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return error_response(FACEAI_SERVICE_UNAVAILABLE_MSG, 
                                status_code=HTTP_SERVICE_UNAVAILABLE)
        
        # Process images
        start_time = time.time()
        result = service.check_ambiguity(filepath1, filepath2, show_result=show_result)
        processing_time = calculate_processing_time(start_time)
        
        if result.get("error"):
            # Check if it's a service unavailable error (ambiguity checker not available)
            if "not available" in result.get("error", "").lower():
                # Return error with additional info if available
                error_data = {
                    "message": result.get("error", "Ambiguity checker not available"),
                    "available_features": result.get("available_features", {}),
                    "suggestion": result.get("suggestion", "")
                }
                return error_response(
                    error_data,
                    status_code=HTTP_SERVICE_UNAVAILABLE
                )
            return error_response(result.get("error"), status_code=HTTP_INTERNAL_ERROR)
        
        # Save to database
        ambiguity_analysis = AmbiguityAnalysis(
            image1_path=filepath1,
            image2_path=filepath2,
            source_type=source_type,
            is_ambiguous=result.get("ambiguous", False),
            ambiguity_score=result.get("score", 0.0),
            similarity_scores=result.get("similarities", {}),
            reasons=result.get("reasons", []),
            processing_time_ms=processing_time,
            model_version=MODEL_VERSION
        )
        success, _ = save_model(ambiguity_analysis)
        if success:
            result["analysis_id"] = ambiguity_analysis.id
        
        return success_response({
            "analysis_id": result.get("analysis_id"),
            "ambiguous": result.get("ambiguous", False),
            "score": result.get("score", 0.0),
            "similarities": result.get("similarities", {}),
            "reasons": result.get("reasons", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        return handle_exception(e, "Ambiguity check", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/detections", methods=["GET"])
def get_detections():
    """Get face detection history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        source_type = request.args.get('source_type')
        
        query = FaceDetection.query
        
        if source_type:
            query = query.filter_by(source_type=source_type)
        
        detections = query.order_by(FaceDetection.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return paginated_response(
            [detection.to_dict() for detection in detections.items],
            page, per_page, detections.total, detections.pages,
            data_key="detections"
        )
        
    except Exception as e:
        return handle_exception(e, "Get detections", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/detections/<detection_id>", methods=["GET"])
def get_detection(detection_id):
    """Get specific face detection result"""
    try:
        detection = FaceDetection.query.get_or_404(detection_id)
        return success_response({"detection": detection.to_dict()})
    except Exception as e:
        return handle_exception(e, "Get detection", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/analyses/demographics", methods=["GET"])
def get_demographics_analyses():
    """Get demographics analysis history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        
        analyses = DemographicsAnalysis.query.order_by(
            DemographicsAnalysis.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return paginated_response(
            [analysis.to_dict() for analysis in analyses.items],
            page, per_page, analyses.total, analyses.pages,
            data_key="analyses"
        )
        
    except Exception as e:
        return handle_exception(e, "Get demographics analyses", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/analyses/ambiguity", methods=["GET"])
def get_ambiguity_analyses():
    """Get ambiguity analysis history"""
    try:
        from app.utils.file_utils import DEFAULT_PAGE_SIZE
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int)
        
        analyses = AmbiguityAnalysis.query.order_by(
            AmbiguityAnalysis.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return paginated_response(
            [analysis.to_dict() for analysis in analyses.items],
            page, per_page, analyses.total, analyses.pages,
            data_key="analyses"
        )
        
    except Exception as e:
        return handle_exception(e, "Get ambiguity analyses", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/configurations", methods=["GET"])
def get_configurations():
    """Get FaceAi configurations"""
    try:
        configs = FaceAiConfiguration.query.filter_by(is_active=True).all()
        return success_response({
            "configurations": [config.to_dict() for config in configs]
        })
    except Exception as e:
        return handle_exception(e, "Get configurations", HTTP_INTERNAL_ERROR)

@faceai_bp.route("/configurations", methods=["POST"])
def create_configuration():
    """Create new FaceAi configuration"""
    try:
        data = request.get_json()
        
        if not data or 'config_name' not in data or 'config_data' not in data:
            return error_response("config_name and config_data required", 
                                status_code=HTTP_BAD_REQUEST)
        
        config = FaceAiConfiguration(
            config_name=data['config_name'],
            config_data=data['config_data'],
            description=data.get('description'),
            created_by=data.get('created_by')
        )
        
        success, error_msg = save_model(config)
        if not success:
            return error_response(error_msg or "Failed to create configuration",
                                status_code=HTTP_INTERNAL_ERROR)
        
        return success_response({"configuration": config.to_dict()}, 
                              status_code=HTTP_CREATED)
        
    except Exception as e:
        return handle_exception(e, "Create configuration", HTTP_INTERNAL_ERROR)
