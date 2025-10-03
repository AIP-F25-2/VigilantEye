from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class FrameSchema(Schema):
    """Frame schema for serialization"""
    id = fields.Integer(dump_only=True)
    frame_type = fields.String(dump_only=True)
    filename = fields.String(dump_only=True)
    file_path = fields.String(dump_only=True)
    offset_seconds = fields.Float(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    width = fields.Integer(dump_only=True)
    height = fields.Integer(dump_only=True)
    file_size = fields.Integer(dump_only=True)
    quality = fields.Integer(dump_only=True)
    batch_id = fields.String(dump_only=True)
    batch_index = fields.Integer(dump_only=True)
    metadata = fields.Dict(dump_only=True)
    video_id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class FrameSnapshotSchema(Schema):
    """Schema for single frame snapshot"""
    video_id = fields.Integer(required=True, validate=validate.Range(min=1))
    offset_seconds = fields.Float(required=True, validate=validate.Range(min=0))
    quality = fields.Integer(missing=2, validate=validate.Range(min=1, max=31))
    width = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    height = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))

class FrameBatchSchema(Schema):
    """Schema for batch frame extraction"""
    video_id = fields.Integer(required=True, validate=validate.Range(min=1))
    start_seconds = fields.Float(missing=0.0, validate=validate.Range(min=0))
    end_seconds = fields.Float(allow_none=True, validate=validate.Range(min=0))
    interval_seconds = fields.Float(required=True, validate=validate.Range(min=0.1, max=3600))
    max_frames = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=10000))
    quality = fields.Integer(missing=2, validate=validate.Range(min=1, max=31))
    width = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    height = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    batch_name = fields.String(allow_none=True, validate=validate.Length(max=255))

    @validates_schema
    def validate_time_range(self, data, **kwargs):
        start_seconds = data.get('start_seconds', 0.0)
        end_seconds = data.get('end_seconds')
        
        if end_seconds is not None and end_seconds <= start_seconds:
            raise ValidationError('end_seconds must be greater than start_seconds')

class FrameBatchUpdateSchema(Schema):
    """Schema for updating frame batch"""
    batch_name = fields.String(validate=validate.Length(max=255))
    is_completed = fields.Boolean()
    error_message = fields.String(allow_none=True, validate=validate.Length(max=1000))

class FrameSearchSchema(Schema):
    """Schema for frame search parameters"""
    video_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    frame_type = fields.String(allow_none=True, validate=validate.OneOf(['single', 'batch', 'auto']))
    batch_id = fields.String(allow_none=True)
    min_offset = fields.Float(allow_none=True, validate=validate.Range(min=0))
    max_offset = fields.Float(allow_none=True, validate=validate.Range(min=0))
    min_quality = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=31))
    max_quality = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=31))
    created_after = fields.DateTime(allow_none=True)
    created_before = fields.DateTime(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    project_id = fields.Integer(allow_none=True)
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = fields.String(missing='created_at', validate=validate.OneOf(['created_at', 'offset_seconds', 'file_size', 'quality']))
    sort_order = fields.String(missing='desc', validate=validate.OneOf(['asc', 'desc']))

    @validates_schema
    def validate_offset_range(self, data, **kwargs):
        min_offset = data.get('min_offset')
        max_offset = data.get('max_offset')
        if min_offset is not None and max_offset is not None and min_offset > max_offset:
            raise ValidationError('min_offset must be less than or equal to max_offset')

    @validates_schema
    def validate_quality_range(self, data, **kwargs):
        min_quality = data.get('min_quality')
        max_quality = data.get('max_quality')
        if min_quality is not None and max_quality is not None and min_quality > max_quality:
            raise ValidationError('min_quality must be less than or equal to max_quality')

class FrameDownloadSchema(Schema):
    """Schema for frame download request"""
    format = fields.String(missing='original', validate=validate.OneOf(['original', 'jpg', 'png', 'webp']))
    quality = fields.Integer(missing=90, validate=validate.Range(min=1, max=100))
    width = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    height = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    as_attachment = fields.Boolean(missing=True)
