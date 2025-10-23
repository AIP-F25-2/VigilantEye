"""
FaceAi API Controller for VIGILANTEye
Provides REST API endpoints for face detection, demographics, and ambiguity analysis
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import time
import logging
from app import db
from app.services.faceai_service import get_faceai_service
from app.models.faceai_models import (
    FaceDetection, DemographicsAnalysis, AmbiguityAnalysis, 
    FaceEncoding, FaceAiConfiguration
)

logger = logging.getLogger(__name__)

# Create blueprint
faceai_bp = Blueprint("faceai", __name__, url_prefix="/api/faceai")

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder="uploads"):
    """Save uploaded file and return path"""
    if file and allowed_file(file.filename):
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

@faceai_bp.route("/status", methods=["GET"])
def get_status():
    """Get FaceAi service status"""
    try:
        service = get_faceai_service()
        status = service.get_service_status()
        return jsonify({
            "success": True,
            "status": status
        })
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/detect", methods=["POST"])
def detect_faces():
    """Detect and recognize faces in an uploaded image"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "faceai")
        if not filepath:
            return jsonify({"error": "Invalid file type"}), 400
        
        # Get additional parameters
        source_type = request.form.get('source_type', 'image')
        video_id = request.form.get('video_id')
        frame_number = request.form.get('frame_number', type=int)
        show_result = request.form.get('show_result', 'false').lower() == 'true'
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return jsonify({"error": "FaceAi service not available"}), 503
        
        # Process image
        start_time = time.time()
        result = service.detect_faces(filepath, show_result=show_result)
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if result.get("error"):
            return jsonify(result), 500
        
        # Save to database
        try:
            face_detection = FaceDetection(
                source_type=source_type,
                source_path=filepath,
                video_id=video_id,
                frame_number=frame_number,
                faces_detected=result.get("faces_detected", 0),
                detection_results=result.get("results"),
                processing_time_ms=processing_time,
                model_version="1.0"
            )
            db.session.add(face_detection)
            db.session.commit()
            
            result["detection_id"] = face_detection.id
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            db.session.rollback()
        
        return jsonify({
            "success": True,
            "detection_id": result.get("detection_id"),
            "faces_detected": result.get("faces_detected", 0),
            "results": result.get("results", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/demographics", methods=["POST"])
def analyze_demographics():
    """Analyze age and gender demographics of faces in an image"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file
        filepath = save_uploaded_file(file, "faceai")
        if not filepath:
            return jsonify({"error": "Invalid file type"}), 400
        
        # Get additional parameters
        source_type = request.form.get('source_type', 'image')
        face_detection_id = request.form.get('face_detection_id')
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return jsonify({"error": "FaceAi service not available"}), 503
        
        # Process image
        start_time = time.time()
        result = service.analyze_demographics(filepath)
        processing_time = (time.time() - start_time) * 1000
        
        if result.get("error"):
            return jsonify(result), 500
        
        # Save to database
        try:
            demographics_analysis = DemographicsAnalysis(
                face_detection_id=face_detection_id,
                source_type=source_type,
                source_path=filepath,
                faces_analyzed=result.get("faces_analyzed", 0),
                analysis_results=result.get("results"),
                processing_time_ms=processing_time,
                model_version="1.0"
            )
            db.session.add(demographics_analysis)
            db.session.commit()
            
            result["analysis_id"] = demographics_analysis.id
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            db.session.rollback()
        
        return jsonify({
            "success": True,
            "analysis_id": result.get("analysis_id"),
            "faces_analyzed": result.get("faces_analyzed", 0),
            "results": result.get("results", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        logger.error(f"Demographics analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/ambiguity", methods=["POST"])
def check_ambiguity():
    """Check if two images show the same person (ambiguity detection)"""
    try:
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({"error": "Two image files required (image1 and image2)"}), 400
        
        file1 = request.files['image1']
        file2 = request.files['image2']
        
        if file1.filename == '' or file2.filename == '':
            return jsonify({"error": "Both files must be selected"}), 400
        
        # Save uploaded files
        filepath1 = save_uploaded_file(file1, "faceai")
        filepath2 = save_uploaded_file(file2, "faceai")
        
        if not filepath1 or not filepath2:
            return jsonify({"error": "Invalid file types"}), 400
        
        # Get additional parameters
        source_type = request.form.get('source_type', 'comparison')
        show_result = request.form.get('show_result', 'false').lower() == 'true'
        
        # Get FaceAi service
        service = get_faceai_service()
        if not service.is_available():
            return jsonify({"error": "FaceAi service not available"}), 503
        
        # Process images
        start_time = time.time()
        result = service.check_ambiguity(filepath1, filepath2, show_result=show_result)
        processing_time = (time.time() - start_time) * 1000
        
        if result.get("error"):
            return jsonify(result), 500
        
        # Save to database
        try:
            ambiguity_analysis = AmbiguityAnalysis(
                image1_path=filepath1,
                image2_path=filepath2,
                source_type=source_type,
                is_ambiguous=result.get("ambiguous", False),
                ambiguity_score=result.get("score", 0.0),
                similarity_scores=result.get("similarities", {}),
                reasons=result.get("reasons", []),
                processing_time_ms=processing_time,
                model_version="1.0"
            )
            db.session.add(ambiguity_analysis)
            db.session.commit()
            
            result["analysis_id"] = ambiguity_analysis.id
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            db.session.rollback()
        
        return jsonify({
            "success": True,
            "analysis_id": result.get("analysis_id"),
            "ambiguous": result.get("ambiguous", False),
            "score": result.get("score", 0.0),
            "similarities": result.get("similarities", {}),
            "reasons": result.get("reasons", []),
            "processing_time_ms": processing_time
        })
        
    except Exception as e:
        logger.error(f"Ambiguity check error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/detections", methods=["GET"])
def get_detections():
    """Get face detection history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        source_type = request.args.get('source_type')
        
        query = FaceDetection.query
        
        if source_type:
            query = query.filter_by(source_type=source_type)
        
        detections = query.order_by(FaceDetection.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "success": True,
            "detections": [detection.to_dict() for detection in detections.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": detections.total,
                "pages": detections.pages
            }
        })
        
    except Exception as e:
        logger.error(f"Get detections error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/detections/<detection_id>", methods=["GET"])
def get_detection(detection_id):
    """Get specific face detection result"""
    try:
        detection = FaceDetection.query.get_or_404(detection_id)
        return jsonify({
            "success": True,
            "detection": detection.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Get detection error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/analyses/demographics", methods=["GET"])
def get_demographics_analyses():
    """Get demographics analysis history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        analyses = DemographicsAnalysis.query.order_by(
            DemographicsAnalysis.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "success": True,
            "analyses": [analysis.to_dict() for analysis in analyses.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": analyses.total,
                "pages": analyses.pages
            }
        })
        
    except Exception as e:
        logger.error(f"Get demographics analyses error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/analyses/ambiguity", methods=["GET"])
def get_ambiguity_analyses():
    """Get ambiguity analysis history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        analyses = AmbiguityAnalysis.query.order_by(
            AmbiguityAnalysis.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "success": True,
            "analyses": [analysis.to_dict() for analysis in analyses.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": analyses.total,
                "pages": analyses.pages
            }
        })
        
    except Exception as e:
        logger.error(f"Get ambiguity analyses error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/configurations", methods=["GET"])
def get_configurations():
    """Get FaceAi configurations"""
    try:
        configs = FaceAiConfiguration.query.filter_by(is_active=True).all()
        return jsonify({
            "success": True,
            "configurations": [config.to_dict() for config in configs]
        })
        
    except Exception as e:
        logger.error(f"Get configurations error: {e}")
        return jsonify({"error": str(e)}), 500

@faceai_bp.route("/configurations", methods=["POST"])
def create_configuration():
    """Create new FaceAi configuration"""
    try:
        data = request.get_json()
        
        if not data or 'config_name' not in data or 'config_data' not in data:
            return jsonify({"error": "config_name and config_data required"}), 400
        
        config = FaceAiConfiguration(
            config_name=data['config_name'],
            config_data=data['config_data'],
            description=data.get('description'),
            created_by=data.get('created_by')
        )
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "configuration": config.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Create configuration error: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
