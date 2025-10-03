from marshmallow import Schema, fields, validate, validates_schema, ValidationError

class SegmentSchema(Schema):
    """Segment schema for serialization"""
    id = fields.Integer(dump_only=True)
    filename = fields.String(dump_only=True)
    file_path = fields.String(dump_only=True)
    segment_index = fields.Integer(dump_only=True)
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
    segment_seconds = fields.Float(dump_only=True)
    keyframe_interval = fields.Integer(dump_only=True)
    segment_metadata = fields.Dict(dump_only=True)
    video_id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    project_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class SegmentCreateSchema(Schema):
    """Schema for creating segments"""
    video_id = fields.Integer(required=True, validate=validate.Range(min=1))
    segment_seconds = fields.Float(required=True, validate=validate.Range(min=1, max=3600))
    quality = fields.String(missing='high', validate=validate.OneOf(['low', 'medium', 'high', 'ultra']))
    keyframe_interval = fields.Integer(allow_none=True, validate=validate.Range(min=1, max=300))
    project_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
