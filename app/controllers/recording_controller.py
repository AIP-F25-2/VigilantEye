from flask import Blueprint, request, jsonify
from app import db
from app.models import Recording, RecordingSession, Device
from app.schemas import RecordingSchema, RecordingStartSchema, RecordingSessionSchema
from marshmallow import ValidationError
from datetime import datetime
import threading
import subprocess
import os
import time

recording_bp = Blueprint('recording_api', __name__)
recording_schema = RecordingSchema()
recordings_schema = RecordingSchema(many=True)
recording_start_schema = RecordingStartSchema()
recording_session_schema = RecordingSessionSchema()

# Global recording state
_recording_lock = threading.Lock()
_active_recording = None

@recording_bp.route('/recordings', methods=['GET'])
def get_recordings():
    """Get all recordings with optional filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_id = request.args.get('user_id', type=int)
        project_id = request.args.get('project_id', type=int)
        status = request.args.get('status')
        
        query = Recording.query
        
        if user_id:
            query = query.filter(Recording.user_id == user_id)
        if project_id:
            query = query.filter(Recording.project_id == project_id)
        if status:
            from app.models.recording import RecordingStatus
            query = query.filter(Recording.status == RecordingStatus(status))
        
        query = query.order_by(Recording.created_at.desc())
        
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': recordings_schema.dump(paginated.items),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/<int:recording_id>', methods=['GET'])
def get_recording(recording_id):
    """Get a specific recording by ID"""
    try:
        recording = Recording.query.get_or_404(recording_id)
        return jsonify({
            'status': 'success',
            'data': recording_schema.dump(recording)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/start', methods=['POST'])
def start_recording():
    """Start a new recording"""
    try:
        data = recording_start_schema.load(request.json)
        
        with _recording_lock:
            if _active_recording and _active_recording.status == RecordingStatus.RECORDING:
                return jsonify({
                    'status': 'error', 
                    'message': 'Another recording is already in progress'
                }), 409
        
        # Create recording record
        recording = Recording(
            mode=data['mode'],
            source=data.get('source'),
            fps=data.get('fps', 30),
            max_duration_seconds=data.get('max_duration_seconds'),
            user_id=data.get('user_id'),
            project_id=data.get('project_id'),
            status=RecordingStatus.STARTING
        )
        
        db.session.add(recording)
        db.session.commit()
        
        # Start recording process
        success = _start_recording_process(recording)
        
        if not success:
            recording.status = RecordingStatus.FAILED
            recording.error_message = "Failed to start recording process"
            db.session.commit()
            return jsonify({
                'status': 'error',
                'message': 'Failed to start recording'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Recording started successfully',
            'data': recording_schema.dump(recording)
        }), 201
        
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/<int:recording_id>/stop', methods=['POST'])
def stop_recording(recording_id):
    """Stop a recording"""
    try:
        recording = Recording.query.get_or_404(recording_id)
        
        with _recording_lock:
            if recording.status != RecordingStatus.RECORDING:
                return jsonify({
                    'status': 'error',
                    'message': 'Recording is not currently active'
                }), 400
            
            recording.status = RecordingStatus.STOPPING
            recording.ended_at = datetime.utcnow()
            
            # Stop the recording process
            if _active_recording and _active_recording.id == recording.id:
                _stop_recording_process()
                _active_recording = None
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Recording stopped successfully',
            'data': recording_schema.dump(recording)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/status', methods=['GET'])
def get_recording_status():
    """Get current recording status"""
    try:
        with _recording_lock:
            if _active_recording:
                return jsonify({
                    'status': 'success',
                    'data': {
                        'is_recording': True,
                        'recording': recording_schema.dump(_active_recording)
                    }
                }), 200
            else:
                return jsonify({
                    'status': 'success',
                    'data': {
                        'is_recording': False,
                        'recording': None
                    }
                }), 200
                
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/devices', methods=['GET'])
def get_recording_devices():
    """Get available recording devices"""
    try:
        devices = Device.query.filter(Device.device_type.in_(['webcam', 'screen', 'rtsp'])).all()
        
        device_schema = DeviceSchema(many=True)
        
        return jsonify({
            'status': 'success',
            'data': device_schema.dump(devices)
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@recording_bp.route('/recordings/sessions', methods=['GET'])
def get_recording_sessions():
    """Get recording sessions"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_id = request.args.get('user_id', type=int)
        
        query = RecordingSession.query
        
        if user_id:
            query = query.filter(RecordingSession.user_id == user_id)
        
        query = query.order_by(RecordingSession.created_at.desc())
        
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': recording_session_schema.dump(paginated.items, many=True),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def _start_recording_process(recording):
    """Start the actual recording process"""
    try:
        # This would integrate with your existing recording logic
        # from app.server.blueprints.record import _start_record
        
        # For now, just update the status
        recording.status = RecordingStatus.RECORDING
        recording.started_at = datetime.utcnow()
        recording.process_id = os.getpid()  # Placeholder
        
        with _recording_lock:
            _active_recording = recording
        
        return True
        
    except Exception as e:
        recording.error_message = str(e)
        return False

def _stop_recording_process():
    """Stop the recording process"""
    try:
        # This would integrate with your existing recording logic
        # from app.server.blueprints.record import stop_recording
        
        # For now, just update the status
        if _active_recording:
            _active_recording.status = RecordingStatus.COMPLETED
            _active_recording.ended_at = datetime.utcnow()
        
        return True
        
    except Exception as e:
        if _active_recording:
            _active_recording.error_message = str(e)
            _active_recording.status = RecordingStatus.FAILED
        return False
