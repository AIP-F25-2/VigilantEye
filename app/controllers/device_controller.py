from flask import Blueprint, request, jsonify
from app import db
from app.models import Device
from app.schemas import DeviceSchema
from marshmallow import ValidationError

device_bp = Blueprint('device_api', __name__)
device_schema = DeviceSchema()
devices_schema = DeviceSchema(many=True)

@device_bp.route('/devices', methods=['GET'])
def get_devices():
    """Get all devices with optional filtering"""
    try:
        # Parse query parameters
        status = request.args.get('status')
        device_type = request.args.get('type')
        
        # Build query
        query = Device.query
        
        # Apply filters
        if status:
            from app.models.device import DeviceStatus
            query = query.filter(Device.status == DeviceStatus(status))
        
        if device_type:
            from app.models.device import DeviceType
            query = query.filter(Device.device_type == DeviceType(device_type))
        
        # Get all devices
        devices = query.all()
        
        return jsonify({
            'status': 'success',
            'data': devices_schema.dump(devices)
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    """Get a specific device by ID"""
    try:
        device = Device.query.get_or_404(device_id)
        return jsonify({
            'status': 'success',
            'data': device_schema.dump(device)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices', methods=['POST'])
def create_device():
    """Create a new device"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['device_id', 'name', 'device_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
        
        # Convert device_type string to enum
        from app.models.device import DeviceType, DeviceStatus
        device_type_enum = DeviceType(data['device_type'])
        
        # Create device
        device = Device(
            device_id=data['device_id'],
            name=data['name'],
            device_type=device_type_enum,
            connection_string=data.get('connection_string'),
            rtsp_url=data.get('rtsp_url'),
            ip_address=data.get('ip_address'),
            port=data.get('port'),
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            version=data.get('version'),
            serial_number=data.get('serial_number'),
            driver=data.get('driver'),
            capabilities=data.get('capabilities', {}),
            supported_formats=data.get('supported_formats', []),
            supported_resolutions=data.get('supported_resolutions', []),
            supported_framerates=data.get('supported_framerates', []),
            default_settings=data.get('default_settings', {}),
            current_settings=data.get('current_settings', {}),
            user_id=data.get('user_id')
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Device created successfully',
            'data': device_schema.dump(device)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id):
    """Update device information"""
    try:
        device = Device.query.get_or_404(device_id)
        data = request.get_json()
        
        # Handle enum fields
        from app.models.device import DeviceType, DeviceStatus
        
        if 'device_type' in data:
            data['device_type'] = DeviceType(data['device_type'])
        
        if 'status' in data:
            data['status'] = DeviceStatus(data['status'])
        
        # Update fields
        for field, value in data.items():
            if hasattr(device, field):
                setattr(device, field, value)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Device updated successfully',
            'data': device_schema.dump(device)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Delete a device"""
    try:
        device = Device.query.get_or_404(device_id)
        
        db.session.delete(device)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Device deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices/<int:device_id>/start', methods=['POST'])
def start_device(device_id):
    """Start a device"""
    try:
        device = Device.query.get_or_404(device_id)
        
        from app.models.device import DeviceStatus
        device.status = DeviceStatus.AVAILABLE
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Device {device.name} started successfully',
            'data': device_schema.dump(device)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_bp.route('/devices/<int:device_id>/stop', methods=['POST'])
def stop_device(device_id):
    """Stop a device"""
    try:
        device = Device.query.get_or_404(device_id)
        
        from app.models.device import DeviceStatus
        device.status = DeviceStatus.OFFLINE
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Device {device.name} stopped successfully',
            'data': device_schema.dump(device)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
