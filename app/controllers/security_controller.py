from flask import Blueprint, request, jsonify
from app.services.threat_detection import threat_detector, ThreatLevel, ThreatType
from datetime import datetime, timedelta
import json

security_bp = Blueprint('security_api', __name__)

@security_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """Get all security alerts with filtering"""
    try:
        # Parse query parameters
        threat_level = request.args.get('threat_level')
        threat_type = request.args.get('threat_type')
        camera_id = request.args.get('camera_id')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        hours = int(request.args.get('hours', 24))
        
        # Get alerts from threat detector
        alerts = threat_detector.threat_history.copy()
        
        # Filter by time
        cutoff_time = datetime.now() - timedelta(hours=hours)
        alerts = [alert for alert in alerts 
                 if datetime.fromisoformat(alert['timestamp']) >= cutoff_time]
        
        # Apply filters
        if threat_level:
            alerts = [alert for alert in alerts if alert['threat_level'] == threat_level]
        
        if threat_type:
            alerts = [alert for alert in alerts if alert['threat_type'] == threat_type]
        
        if camera_id:
            alerts = [alert for alert in alerts if alert['camera_id'] == camera_id]
        
        if active_only:
            alerts = [alert for alert in alerts if not alert.get('resolved', False)]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': alerts,
            'count': len(alerts)
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/alerts/active', methods=['GET'])
def get_active_alerts():
    """Get currently active security alerts"""
    try:
        active_alerts = threat_detector.get_active_threats()
        
        return jsonify({
            'status': 'success',
            'data': active_alerts,
            'count': len(active_alerts)
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/alerts/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge a security alert"""
    try:
        threat_detector.acknowledge_alert(alert_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Alert acknowledged successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve a security alert"""
    try:
        threat_detector.resolve_alert(alert_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Alert resolved successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """Get security alert statistics"""
    try:
        stats = threat_detector.get_threat_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/detection/start/<camera_id>', methods=['POST'])
def start_detection(camera_id):
    """Start threat detection for a camera"""
    try:
        data = request.get_json() or {}
        stream_url = data.get('stream_url', f'rtsp://192.168.1.100:554/stream1')
        
        success = threat_detector.start_detection(camera_id, stream_url)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Threat detection started for camera {camera_id}'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to start detection for camera {camera_id}'
            }), 400
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/detection/stop/<camera_id>', methods=['POST'])
def stop_detection(camera_id):
    """Stop threat detection for a camera"""
    try:
        threat_detector.stop_detection(camera_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Threat detection stopped for camera {camera_id}'
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/emergency/panic', methods=['POST'])
def emergency_panic():
    """Trigger emergency panic alert"""
    try:
        data = request.get_json() or {}
        location = data.get('location', 'Unknown')
        description = data.get('description', 'Emergency panic button activated')
        
        # Create critical emergency alert
        alert = {
            'id': f"emergency_{int(datetime.now().timestamp())}",
            'camera_id': 'emergency',
            'threat_type': 'emergency',
            'threat_level': 'critical',
            'confidence': 1.0,
            'description': f"🚨 EMERGENCY PANIC: {description} at {location}",
            'timestamp': datetime.now().isoformat(),
            'bbox': None,
            'acknowledged': False,
            'resolved': False,
            'emergency': True
        }
        
        threat_detector.threat_history.append(alert)
        
        return jsonify({
            'status': 'success',
            'message': 'Emergency alert triggered',
            'alert_id': alert['id']
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@security_bp.route('/emergency/status', methods=['GET'])
def get_emergency_status():
    """Get current emergency status"""
    try:
        # Check for active emergency alerts
        emergency_alerts = [alert for alert in threat_detector.threat_history 
                           if alert.get('emergency', False) and not alert.get('resolved', False)]
        
        status = {
            'emergency_active': len(emergency_alerts) > 0,
            'active_emergencies': len(emergency_alerts),
            'last_emergency': emergency_alerts[0]['timestamp'] if emergency_alerts else None,
            'total_threats_24h': len([a for a in threat_detector.threat_history 
                                    if (datetime.now() - datetime.fromisoformat(a['timestamp'])).days < 1])
        }
        
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
