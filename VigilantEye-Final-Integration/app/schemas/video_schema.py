from marshmallow import Schema, fields, validate, validates_schema, ValidationError
from datetime import datetime

class VideoSchema(Schema):
    """Video schema for serialization"""
    id = fields.Integer(dump_only=True)
    filename = fields.String(dump_only=True)
    original_filename = fields.String(dump_only=True)
    stored_path = fields.String(dump_only=True)
    stored_name = fields.String(dump_only=True)
    size_bytes = fields.Integer(dump_only=True)
    size_human = fields.String(dump_only=True)
    checksum = fields.String(dump_only=True)
    mimetype = fields.String(dump_only=True)
    duration_seconds = fields.Float(dump_only=True)
    width = fields.Integer(dump_only=True)
    height = fields.Integer(dump_only=True)
    fps = fields.Float(dump_only=True)
    bitrate = fields.Integer(dump_only=True)
    codec = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    metadata = fields.Dict(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class VideoUploadSchema(Schema):
    """Schema for video upload validation"""
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    tags = fields.List(fields.String(), allow_none=True)
    category = fields.String(allow_none=True, validate=validate.Length(max=100))
    is_public = fields.Boolean(missing=False)
    allow_download = fields.Boolean(missing=True)
    allow_streaming = fields.Boolean(missing=True)

class VideoUpdateSchema(Schema):
    """Schema for video update validation"""
    filename = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    tags = fields.List(fields.String(), allow_none=True)
    category = fields.String(allow_none=True, validate=validate.Length(max=100))
    is_public = fields.Boolean()
    allow_download = fields.Boolean()
    allow_streaming = fields.Boolean()
    metadata = fields.Dict(allow_none=True)

class VideoSearchSchema(Schema):
    """Schema for video search parameters"""
    query = fields.String(allow_none=True, validate=validate.Length(max=255))
    category = fields.String(allow_none=True)
    tags = fields.List(fields.String(), allow_none=True)
    min_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    max_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    min_size = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    max_size = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    status = fields.String(allow_none=True, validate=validate.OneOf(['uploading', 'processing', 'ready', 'error', 'deleted']))
    created_after = fields.DateTime(allow_none=True)
    created_before = fields.DateTime(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    project_id = fields.Integer(allow_none=True)
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = fields.String(missing='created_at', validate=validate.OneOf(['created_at', 'filename', 'size_bytes', 'duration_seconds']))
    sort_order = fields.String(missing='desc', validate=validate.OneOf(['asc', 'desc']))

    @validates_schema
    def validate_duration_range(self, data, **kwargs):
        min_duration = data.get('min_duration')
        max_duration = data.get('max_duration')
        if min_duration is not None and max_duration is not None and min_duration > max_duration:
            raise ValidationError('min_duration must be less than or equal to max_duration')

    @validates_schema
    def validate_size_range(self, data, **kwargs):
        min_size = data.get('min_size')
        max_size = data.get('max_size')
        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValidationError('min_size must be less than or equal to max_size')

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        created_after = data.get('created_after')
        created_before = data.get('created_before')
        if created_after is not None and created_before is not None and created_after > created_before:
            raise ValidationError('created_after must be before created_before')

class VideoMetadataSchema(Schema):
    """Schema for video metadata"""
    key = fields.String(required=True, validate=validate.Length(min=1, max=100))
    value = fields.String(required=True)
    data_type = fields.String(validate=validate.OneOf(['string', 'int', 'float', 'json', 'bool']), missing='string')

class VideoSearchSchema(Schema):
    """Schema for video search parameters"""
    query = fields.String(allow_none=True, validate=validate.Length(max=255))
    category = fields.String(allow_none=True)
    tags = fields.List(fields.String(), allow_none=True)
    min_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    max_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    min_size = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    max_size = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    status = fields.String(allow_none=True, validate=validate.OneOf(['uploading', 'processing', 'ready', 'error', 'deleted']))
    created_after = fields.DateTime(allow_none=True)
    created_before = fields.DateTime(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    project_id = fields.Integer(allow_none=True)
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = fields.String(missing='created_at', validate=validate.OneOf(['created_at', 'filename', 'size_bytes', 'duration_seconds']))
    sort_order = fields.String(missing='desc', validate=validate.OneOf(['asc', 'desc']))

    @validates_schema
    def validate_duration_range(self, data, **kwargs):
        min_duration = data.get('min_duration')
        max_duration = data.get('max_duration')
        if min_duration is not None and max_duration is not None and min_duration > max_duration:
            raise ValidationError('min_duration must be less than or equal to max_duration')

    @validates_schema
    def validate_size_range(self, data, **kwargs):
        min_size = data.get('min_size')
        max_size = data.get('max_size')
        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValidationError('min_size must be less than or equal to max_size')

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        created_after = data.get('created_after')
        created_before = data.get('created_before')
        if created_after is not None and created_before is not None and created_after > created_before:
            raise ValidationError('created_after must be before created_before')
