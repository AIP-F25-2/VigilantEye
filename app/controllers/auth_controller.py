from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from app.schemas import LoginSchema, RegisterSchema, TokenResponseSchema, UserResponseSchema
from app.utils.auth_utils import create_user, verify_password, create_tokens

auth_bp = Blueprint('auth', __name__)

# Initialize schemas
login_schema = LoginSchema()
register_schema = RegisterSchema()
token_response_schema = TokenResponseSchema()
user_response_schema = UserResponseSchema()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json(force=True)
        
        # Validate input data
        try:
            validated_data = register_schema.load(data)
        except ValidationError as err:
            return jsonify({
                "error": "Validation error",
                "details": err.messages
            }), 400
        
        # Create user
        try:
            user_data = create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                roles=validated_data.get('roles', ['operator']),
                site_id=validated_data.get('site_id', 'default'),
                username=validated_data.get('username')
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        return jsonify({
            "id": user_data["id"],
            "email": user_data["email"],
            "roles": user_data["roles"],
            "site_id": user_data["site_id"]
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT tokens"""
    try:
        data = request.get_json(force=True)
        
        # Validate input data
        try:
            validated_data = login_schema.load(data)
        except ValidationError as err:
            return jsonify({
                "error": "Validation error",
                "details": err.messages
            }), 400
        
        # Verify credentials
        user_data = verify_password(validated_data['email'], validated_data['password'])
        if not user_data:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Create tokens
        access_token, refresh_token = create_tokens(user_data)
        
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token using refresh token"""
    from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
    from datetime import timedelta
    
    try:
        # Get current user identity from refresh token
        current_user = get_jwt_identity()
        
        # Create new access token
        new_access_token = create_access_token(
            identity=current_user,
            expires_delta=timedelta(hours=2)
        )
        
        return jsonify({
            "access_token": new_access_token
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to refresh token",
            "message": str(e)
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user by revoking tokens"""
    from flask_jwt_extended import jwt_required, get_jwt, revoke_token
    
    try:
        # Get JWT token info
        jti = get_jwt()['jti']
        
        # Revoke token
        revoke_token(jti)
        
        return jsonify({
            "message": "Successfully logged out"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to logout",
            "message": str(e)
        }), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from app.models.user import User
    
    try:
        current_user_id = get_jwt_identity()['id']
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user_response_schema.dump(user)), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to get user information",
            "message": str(e)
        }), 500
