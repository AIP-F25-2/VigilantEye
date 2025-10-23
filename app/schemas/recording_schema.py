from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class RecordingSchema(Schema):
    """Recording schema for serialization"""
    id = fields.Integer(dump_only=True)
    mode = fields.String(dump_only=True)
    source = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    fps = fields.Integer(dump_only=True)
    duration_seconds = fields.Float(dump_only=True)
    max_duration_seconds = fields.Float(dump_only=True)
    output_path = fields.String(dump_only=True)
    log_path = fields.String(dump_only=True)
    process_id = fields.Integer(dump_only=True)
    started_at = fields.DateTime(dump_only=True)
    ended_at = fields.DateTime(dump_only=True)
    settings = fields.Dict(dump_only=True)
    error_message = fields.String(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    video_id = fields.Integer(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class RecordingStartSchema(Schema):
    """Schema for starting a recording"""
    mode = fields.String(required=True, validate=validate.OneOf(['screen', 'rtsp', 'webcam', 'file']))
    source = fields.String(allow_none=True, validate=validate.Length(max=500))
    fps = fields.Integer(missing=30, validate=validate.Range(min=1, max=120))
    max_duration_seconds = fields.Float(allow_none=True, validate=validate.Range(min=1))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    
    # Mode-specific validations
    @validates_schema
    def validate_mode_specific(self, data, **kwargs):
        mode = data.get('mode')
        source = data.get('source')
        
        if mode == 'rtsp':
            if not source or not source.startswith('rtsp://'):
                raise ValidationError('RTSP mode requires a valid rtsp:// URL in source field')
        elif mode == 'webcam':
            if not source:
                raise ValidationError('Webcam mode requires a device name in source field')
        elif mode == 'file':
            if not source:
                raise ValidationError('File mode requires a video_id in source field')

class RecordingStopSchema(Schema):
    """Schema for stopping a recording"""
    save_to_project = fields.Boolean(missing=True)
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))

class RecordingSessionSchema(Schema):
    """Recording session schema"""
    id = fields.Integer(dump_only=True)
    session_id = fields.String(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    name = fields.String(allow_none=True, validate=validate.Length(max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    started_at = fields.DateTime(dump_only=True)
    ended_at = fields.DateTime(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    total_recordings = fields.Integer(dump_only=True)
    total_duration = fields.Float(dump_only=True)
    settings = fields.Dict(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class RecordingSessionCreateSchema(Schema):
    """Schema for creating a recording session"""
    name = fields.String(allow_none=True, validate=validate.Length(max=255))
    description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    settings = fields.Dict(allow_none=True)

class RecordingDeviceSchema(Schema):
    """Schema for recording device information"""
    device_id = fields.String(required=True)
    name = fields.String(required=True)
    device_type = fields.String(required=True, validate=validate.OneOf(['webcam', 'screen', 'rtsp', 'audio', 'file']))
    status = fields.String(dump_only=True)
    capabilities = fields.Dict(dump_only=True)
    supported_formats = fields.List(fields.String(), dump_only=True)
    supported_resolutions = fields.List(fields.String(), dump_only=True)
    supported_framerates = fields.List(fields.Integer(), dump_only=True)
    connection_string = fields.String(dump_only=True)
    rtsp_url = fields.String(dump_only=True)
    manufacturer = fields.String(dump_only=True)
    model = fields.String(dump_only=True)
    is_default = fields.Boolean(dump_only=True)
