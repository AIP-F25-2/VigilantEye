from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class ClipSchema(Schema):
    """Clip schema for serialization"""
    id = fields.Integer(dump_only=True)
    filename = fields.String(dump_only=True)
    file_path = fields.String(dump_only=True)
    start_seconds = fields.Float(dump_only=True)
    end_seconds = fields.Float(dump_only=True)
    duration_seconds = fields.Float(dump_only=True)
    file_size = fields.Integer(dump_only=True)
    file_size_human = fields.String(dump_only=True)
    width = fields.Integer(dump_only=True)
    height = fields.Integer(dump_only=True)
    fps = fields.Float(dump_only=True)
    bitrate = fields.Integer(dump_only=True)
    status = fields.String(dump_only=True)
    processing_started_at = fields.DateTime(dump_only=True)
    processing_completed_at = fields.DateTime(dump_only=True)
    error_message = fields.String(dump_only=True)
    watermark_text = fields.String(dump_only=True)
    watermark_position = fields.String(dump_only=True)
    effects = fields.Dict(dump_only=True)
    metadata = fields.Dict(dump_only=True)
    video_id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ClipCreateSchema(Schema):
    """Schema for creating a clip"""
    video_id = fields.Integer(required=True, validate=validate.Range(min=1))
    start_seconds = fields.Float(required=True, validate=validate.Range(min=0))
    end_seconds = fields.Float(required=True, validate=validate.Range(min=0))
    watermark_text = fields.String(allow_none=True, validate=validate.Length(max=500))
    watermark_position = fields.String(missing='bottom-right', 
                                     validate=validate.OneOf(['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center']))
    quality = fields.String(missing='high', validate=validate.OneOf(['low', 'medium', 'high', 'ultra']))
    fps = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=120))
    bitrate = fields.Integer(allow_none=True, validate=validate.Range(min=100, max=50000))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    effects = fields.Dict(allow_none=True)

    @validates_schema
    def validate_time_range(self, data, **kwargs):
        start_seconds = data.get('start_seconds')
        end_seconds = data.get('end_seconds')
        
        if end_seconds <= start_seconds:
            raise ValidationError('end_seconds must be greater than start_seconds')

class ClipUpdateSchema(Schema):
    """Schema for updating a clip"""
    watermark_text = fields.String(allow_none=True, validate=validate.Length(max=500))
    watermark_position = fields.String(validate=validate.OneOf(['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center']))
    effects = fields.Dict(allow_none=True)
    metadata = fields.Dict(allow_none=True)

class ClipSearchSchema(Schema):
    """Schema for clip search parameters"""
    video_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    status = fields.String(allow_none=True, validate=validate.OneOf(['processing', 'ready', 'error', 'deleted']))
    min_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    max_duration = fields.Float(allow_none=True, validate=validate.Range(min=0))
    min_start_time = fields.Float(allow_none=True, validate=validate.Range(min=0))
    max_start_time = fields.Float(allow_none=True, validate=validate.Range(min=0))
    has_watermark = fields.Boolean(allow_none=True)
    created_after = fields.DateTime(allow_none=True)
    created_before = fields.DateTime(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    project_id = fields.Integer(allow_none=True)
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))
    sort_by = fields.String(missing='created_at', validate=validate.OneOf(['created_at', 'start_seconds', 'duration_seconds', 'file_size']))
    sort_order = fields.String(missing='desc', validate=validate.OneOf(['asc', 'desc']))

    @validates_schema
    def validate_duration_range(self, data, **kwargs):
        min_duration = data.get('min_duration')
        max_duration = data.get('max_duration')
        if min_duration is not None and max_duration is not None and min_duration > max_duration:
            raise ValidationError('min_duration must be less than or equal to max_duration')

    @validates_schema
    def validate_start_time_range(self, data, **kwargs):
        min_start_time = data.get('min_start_time')
        max_start_time = data.get('max_start_time')
        if min_start_time is not None and max_start_time is not None and min_start_time > max_start_time:
            raise ValidationError('min_start_time must be less than or equal to max_start_time')

class ClipBatchCreateSchema(Schema):
    """Schema for creating multiple clips at once"""
    video_id = fields.Integer(required=True, validate=validate.Range(min=1))
    clips = fields.List(fields.Nested(ClipCreateSchema), required=True, validate=validate.Length(min=1, max=50))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    batch_name = fields.String(allow_none=True, validate=validate.Length(max=255))

class ClipDownloadSchema(Schema):
    """Schema for clip download request"""
    format = fields.String(missing='original', validate=validate.OneOf(['original', 'mp4', 'avi', 'mov', 'mkv']))
    quality = fields.String(missing='high', validate=validate.OneOf(['low', 'medium', 'high', 'ultra']))
    fps = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=120))
    bitrate = fields.Integer(allow_none=True, validate=validate.Range(min=100, max=50000))
    as_attachment = fields.Boolean(missing=True)
