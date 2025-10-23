from flask import Blueprint, request, jsonify
from app import db
from app.models import Project, ProjectMember, User
from app.schemas import ProjectSchema, ProjectCreateSchema, ProjectMemberSchema
from marshmallow import ValidationError
from datetime import datetime
from uuid import uuid4

project_bp = Blueprint('project_api', __name__)
project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)
project_create_schema = ProjectCreateSchema()
project_member_schema = ProjectMemberSchema()
project_members_schema = ProjectMemberSchema(many=True)

@project_bp.route('/projects', methods=['GET'])
def get_projects():
    """Get all projects with optional filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        is_public = request.args.get('is_public', type=bool)
        
        query = Project.query
        
        if user_id:
            # Get projects where user is owner or member
            query = query.filter(
                (Project.owner_id == user_id) | 
                (Project.members.any(ProjectMember.user_id == user_id))
            )
        
        if status:
            from app.models.project import ProjectStatus
            query = query.filter(Project.status == ProjectStatus(status))
        
        if is_public is not None:
            query = query.filter(Project.is_public == is_public)
        
        query = query.order_by(Project.created_at.desc())
        
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'status': 'success',
            'data': projects_schema.dump(paginated.items),
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

@project_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID"""
    try:
        project = Project.query.get_or_404(project_id)
        return jsonify({
            'status': 'success',
            'data': project_schema.dump(project)
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = project_create_schema.load(request.json)
        
        # Get user ID from request (in real app, from auth token)
        user_id = data.get('user_id') or request.headers.get('X-User-ID', type=int)
        if not user_id:
            return jsonify({'status': 'error', 'message': 'User ID required'}), 400
        
        # Create project
        project = Project(
            name=data['name'],
            description=data.get('description'),
            owner_id=user_id,
            settings=data.get('settings', {}),
            storage_quota_bytes=data.get('storage_quota_bytes'),
            is_public=data.get('is_public', False),
            allow_guest_upload=data.get('allow_guest_upload', False),
            tags=data.get('tags', []),
            category=data.get('category')
        )
        
        db.session.add(project)
        db.session.flush()  # Get project ID
        
        # Add owner as project member
        owner_member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role='owner',
            joined_at=datetime.utcnow(),
            can_upload=True,
            can_edit=True,
            can_delete=True,
            can_invite=True
        )
        
        db.session.add(owner_member)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project created successfully',
            'data': project_schema.dump(project)
        }), 201
        
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': e.messages}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project details"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions (in real app, verify user can edit)
        user_id = request.headers.get('X-User-ID', type=int)
        if not _can_edit_project(project, user_id):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        data = request.json
        
        # Update fields
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        if 'is_public' in data:
            project.is_public = data['is_public']
        if 'allow_guest_upload' in data:
            project.allow_guest_upload = data['allow_guest_upload']
        if 'tags' in data:
            project.tags = data['tags']
        if 'category' in data:
            project.category = data['category']
        if 'settings' in data:
            project.settings = data['settings']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project updated successfully',
            'data': project_schema.dump(project)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions (in real app, verify user can delete)
        user_id = request.headers.get('X-User-ID', type=int)
        if not _can_delete_project(project, user_id):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        # Soft delete by changing status
        from app.models.project import ProjectStatus
        project.status = ProjectStatus.DELETED
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects/<int:project_id>/members', methods=['GET'])
def get_project_members(project_id):
    """Get project members"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions
        user_id = request.headers.get('X-User-ID', type=int)
        if not _can_view_project(project, user_id):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        members = ProjectMember.query.filter_by(project_id=project_id, is_active=True).all()
        
        return jsonify({
            'status': 'success',
            'data': project_members_schema.dump(members)
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects/<int:project_id>/members', methods=['POST'])
def add_project_member(project_id):
    """Add a member to project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions
        user_id = request.headers.get('X-User-ID', type=int)
        if not _can_invite_to_project(project, user_id):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        data = request.json
        member_user_id = data.get('user_id')
        role = data.get('role', 'viewer')
        
        if not member_user_id:
            return jsonify({'status': 'error', 'message': 'User ID required'}), 400
        
        # Check if user exists
        user = User.query.get(member_user_id)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Check if already a member
        existing_member = ProjectMember.query.filter_by(
            project_id=project_id, 
            user_id=member_user_id
        ).first()
        
        if existing_member:
            if existing_member.is_active:
                return jsonify({'status': 'error', 'message': 'User is already a member'}), 409
            else:
                # Reactivate member
                existing_member.is_active = True
                existing_member.role = role
                existing_member.joined_at = datetime.utcnow()
        else:
            # Create new member
            member = ProjectMember(
                project_id=project_id,
                user_id=member_user_id,
                role=role,
                joined_at=datetime.utcnow(),
                invited_by_id=user_id,
                invitation_token=str(uuid4()),
                can_upload=role in ['owner', 'admin', 'editor'],
                can_edit=role in ['owner', 'admin', 'editor'],
                can_delete=role in ['owner', 'admin'],
                can_invite=role in ['owner', 'admin']
            )
            db.session.add(member)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Member added successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/projects/<int:project_id>/members/<int:member_id>', methods=['DELETE'])
def remove_project_member(project_id, member_id):
    """Remove a member from project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check permissions
        user_id = request.headers.get('X-User-ID', type=int)
        if not _can_manage_members(project, user_id):
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        member = ProjectMember.query.filter_by(
            project_id=project_id, 
            id=member_id
        ).first()
        
        if not member:
            return jsonify({'status': 'error', 'message': 'Member not found'}), 404
        
        # Don't allow removing the owner
        if member.role == 'owner':
            return jsonify({'status': 'error', 'message': 'Cannot remove project owner'}), 400
        
        member.is_active = False
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Member removed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

def _can_view_project(project, user_id):
    """Check if user can view project"""
    if not user_id:
        return project.is_public
    
    # Owner can always view
    if project.owner_id == user_id:
        return True
    
    # Check if user is an active member
    member = ProjectMember.query.filter_by(
        project_id=project.id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    return member is not None

def _can_edit_project(project, user_id):
    """Check if user can edit project"""
    if not user_id:
        return False
    
    # Owner can always edit
    if project.owner_id == user_id:
        return True
    
    # Check if user is admin or editor
    member = ProjectMember.query.filter_by(
        project_id=project.id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    return member and member.role in ['owner', 'admin', 'editor']

def _can_delete_project(project, user_id):
    """Check if user can delete project"""
    if not user_id:
        return False
    
    # Only owner can delete
    return project.owner_id == user_id

def _can_invite_to_project(project, user_id):
    """Check if user can invite to project"""
    if not user_id:
        return False
    
    # Owner and admin can invite
    if project.owner_id == user_id:
        return True
    
    member = ProjectMember.query.filter_by(
        project_id=project.id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    return member and member.role in ['owner', 'admin']

def _can_manage_members(project, user_id):
    """Check if user can manage members"""
    if not user_id:
        return False
    
    # Owner and admin can manage members
    if project.owner_id == user_id:
        return True
    
    member = ProjectMember.query.filter_by(
        project_id=project.id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    return member and member.role in ['owner', 'admin']
