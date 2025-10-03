from flask import Blueprint, request, jsonify, send_file
from app import db
from app.models import Video, VideoMetadata
from app.schemas import VideoSchema, VideoUploadSchema, VideoUpdateSchema, VideoSearchSchema
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
import os
import hashlib
import mimetypes
from datetime import datetime

video_bp = Blueprint('video_api', __name__)
video_schema = VideoSchema()
videos_schema = VideoSchema(many=True)
video_upload_schema = VideoUploadSchema()
video_update_schema = VideoUpdateSchema()
video_search_schema = VideoSearchSchema()

@video_bp.route('/videos', methods=['GET'])
def get_videos():
    """Get all videos with optional filtering and pagination"""
    try:
        # Parse search parameters
        search_params = video_search_schema.load(request.args)
        
        # Build query
        query = Video.query
        
        # Apply filters
        if search_params.get('query'):
            query = query.filter(Video.filename.ilike(f"%{search_params['query']}%"))
        
        if search_params.get('category'):
            query = query.filter(Video.metadata['category'].astext == search_params['category'])
        
        if search_params.get('status'):
            from app.models.video import VideoStatus
            query = query.filter(Video.status == VideoStatus(search_params['status']))
        
        if search_params.get('user_id'):
            query = query.filter(Video.user_id == search_params['user_id'])
        
        if search_params.get('project_id'):
            query = query.filter(Video.project_id == search_params['project_id'])
        
        if search_params.get('min_duration'):
            query = query.filter(Video.duration_seconds >= search_params['min_duration'])
        
        if search_params.get('max_duration'):
            query = query.filter(Video.duration_seconds <= search_params['max_duration'])
        
        if search_params.get('created_after'):
            query = query.filter(Video.created_at >= search_params['created_after'])
        
        if search_params.get('created_before'):
            query = query.filter(Video.created_at <= search_params['created_before'])
        
        # Apply sorting
        sort_by = search_params.get('sort_by', 'created_at')
        sort_order = search_params.get('sort_order', 'desc')
        
        if hasattr(Video, sort_by):
            if sort_order == 'desc':
                query = query.order_by(getattr(Video, sort_by).desc())
            else:
                query = query.order_by(getattr(Video, sort_by).asc())
        
        # Apply pagination
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 20)
        
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': videos_schema.dump(paginated.items),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': e.messages}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos/<int:video_id>', methods=['GET'])
def get_video(video_id):
    """Get a specific video by ID"""
    try:
        video = Video.query.get_or_404(video_id)
        return jsonify({
            'status': 'success',
            'data': video_schema.dump(video)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos', methods=['POST'])
def upload_video():
    """Upload a new video"""
    try:
        # Validate upload parameters
        upload_data = video_upload_schema.load(request.form)
        
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'.mp4', '.mov', '.mkv', '.avi', '.webm'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                'status': 'error', 
                'message': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'
            }), 400
        
        # Generate unique filename
        from uuid import uuid4
        video_id = uuid4().hex
        secure_name = secure_filename(file.filename)
        stored_name = f"{video_id}__{secure_name}"
        
        # Create video directory
        video_dir = os.path.join('data', 'videos')
        os.makedirs(video_dir, exist_ok=True)
        stored_path = os.path.join(video_dir, stored_name)
        
        # Save file
        file.save(stored_path)
        
        # Get file info
        file_size = os.path.getsize(stored_path)
        file_size_human = f"{file_size / 1024 / 1024:.1f} MB"
        
        # Calculate checksum
        with open(stored_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Get MIME type
        mime_type = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
        
        # Create video record
        video = Video(
            filename=secure_name,
            original_filename=file.filename,
            stored_path=stored_path,
            stored_name=stored_name,
            size_bytes=file_size,
            size_human=file_size_human,
            checksum=checksum,
            mimetype=mime_type,
            user_id=upload_data.get('user_id'),
            project_id=upload_data.get('project_id'),
            metadata={
                'description': upload_data.get('description'),
                'tags': upload_data.get('tags', []),
                'category': upload_data.get('category'),
                'is_public': upload_data.get('is_public', False),
                'allow_download': upload_data.get('allow_download', True),
                'allow_streaming': upload_data.get('allow_streaming', True)
            }
        )
        
        db.session.add(video)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Video uploaded successfully',
            'data': video_schema.dump(video)
        }), 201
        
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos/<int:video_id>', methods=['PUT'])
def update_video(video_id):
    """Update video metadata"""
    try:
        video = Video.query.get_or_404(video_id)
        update_data = video_update_schema.load(request.json)
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(video, field):
                setattr(video, field, value)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Video updated successfully',
            'data': video_schema.dump(video)
        }), 200
        
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    """Delete a video and its associated files"""
    try:
        video = Video.query.get_or_404(video_id)
        
        # Delete physical file
        if os.path.exists(video.stored_path):
            os.remove(video.stored_path)
        
        # Delete from database
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Video deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos/<int:video_id>/stream', methods=['GET'])
def stream_video(video_id):
    """Stream video with range support"""
    try:
        video = Video.query.get_or_404(video_id)
        
        if not os.path.exists(video.stored_path):
            return jsonify({'status': 'error', 'message': 'Video file not found'}), 404
        
        # Check if streaming is allowed
        if not video.metadata.get('allow_streaming', True):
            return jsonify({'status': 'error', 'message': 'Streaming not allowed for this video'}), 403
        
        # Handle range requests
        range_header = request.headers.get('Range')
        if range_header:
            # Implement range request handling
            from app.server.utils import stream_bytes
            return stream_bytes(video.stored_path, None, None, video.mimetype)
        else:
            return send_file(video.stored_path, mimetype=video.mimetype, as_attachment=False)
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@video_bp.route('/videos/<int:video_id>/download', methods=['GET'])
def download_video(video_id):
    """Download video file"""
    try:
        video = Video.query.get_or_404(video_id)
        
        if not os.path.exists(video.stored_path):
            return jsonify({'status': 'error', 'message': 'Video file not found'}), 404
        
        # Check if download is allowed
        if not video.metadata.get('allow_download', True):
            return jsonify({'status': 'error', 'message': 'Download not allowed for this video'}), 403
        
        return send_file(video.stored_path, as_attachment=True, download_name=video.original_filename)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
