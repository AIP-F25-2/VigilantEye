from flask import Blueprint, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'message': 'Flask REST API is running!',
        'status': 'success'
    })

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is operational'
    })
