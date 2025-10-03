from marshmallow import Schema, fields, validate

class ProjectSchema(Schema):
    """Project schema for serialization"""
    id = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    project_settings = fields.Dict(dump_only=True)
    storage_quota_bytes = fields.Integer(dump_only=True)
    used_storage_bytes = fields.Integer(dump_only=True)
    is_public = fields.Boolean(dump_only=True)
    allow_guest_upload = fields.Boolean(dump_only=True)
    tags = fields.List(fields.String(), dump_only=True)
    category = fields.String(dump_only=True)
    total_videos = fields.Integer(dump_only=True)
    total_recordings = fields.Integer(dump_only=True)
    total_duration = fields.Float(dump_only=True)
    owner_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ProjectCreateSchema(Schema):
    """Schema for creating projects"""
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    project_settings = fields.Dict(allow_none=True)
    storage_quota_bytes = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    is_public = fields.Boolean(missing=False)
    allow_guest_upload = fields.Boolean(missing=False)
    tags = fields.List(fields.String(), allow_none=True)
    category = fields.String(allow_none=True, validate=validate.Length(max=100))
    user_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))

class ProjectMemberSchema(Schema):
    """Project member schema"""
    id = fields.Integer(dump_only=True)
    role = fields.String(dump_only=True)
    joined_at = fields.DateTime(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    can_upload = fields.Boolean(dump_only=True)
    can_edit = fields.Boolean(dump_only=True)
    can_delete = fields.Boolean(dump_only=True)
    can_invite = fields.Boolean(dump_only=True)
    invited_by_id = fields.Integer(dump_only=True)
    invitation_token = fields.String(dump_only=True)
    invitation_expires_at = fields.DateTime(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
