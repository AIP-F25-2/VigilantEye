from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.schemas.user_schema import UserSchema
from marshmallow import ValidationError

api_bp = Blueprint('api', __name__)
user_schema = UserSchema()
users_schema = UserSchema(many=True)

@api_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify({
            'status': 'success',
            'data': users_schema.dump(users)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user by ID"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'status': 'success',
            'data': user_schema.dump(user)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate input data
        try:
            validated_data = user_schema.load(data)
        except ValidationError as err:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': err.messages
            }), 400
        
        # Check if user already exists
        if User.query.filter_by(email=validated_data['email']).first():
            return jsonify({
                'status': 'error',
                'message': 'User with this email already exists'
            }), 400
        
        if User.query.filter_by(username=validated_data['username']).first():
            return jsonify({
                'status': 'error',
                'message': 'User with this username already exists'
            }), 400
        
        # Create new user
        user = User(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        
        user.save()
        
        return jsonify({
            'status': 'success',
            'message': 'User created successfully',
            'data': user_schema.dump(user)
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update a user by ID"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Validate input data
        try:
            validated_data = user_schema.load(data, partial=True)
        except ValidationError as err:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': err.messages
            }), 400
        
        # Update user fields
        if 'username' in validated_data:
            user.username = validated_data['username']
        if 'email' in validated_data:
            user.email = validated_data['email']
        if 'password' in validated_data:
            user.set_password(validated_data['password'])
        
        user.save()
        
        return jsonify({
            'status': 'success',
            'message': 'User updated successfully',
            'data': user_schema.dump(user)
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user by ID"""
    try:
        user = User.query.get_or_404(user_id)
        user.delete()
        
        return jsonify({
            'status': 'success',
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
