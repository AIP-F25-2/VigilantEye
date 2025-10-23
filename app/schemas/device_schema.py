from marshmallow import Schema, fields, validate
from app.models.device import DeviceType, DeviceStatus

class DeviceSchema(Schema):
    """Device schema for serialization"""
    id = fields.Integer(dump_only=True)
    device_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    device_type = fields.Method('get_device_type')
    status = fields.Method('get_status')
    is_default = fields.Boolean(dump_only=True)
    driver = fields.String(allow_none=True, validate=validate.Length(max=100))
    capabilities = fields.Dict(allow_none=True)
    supported_formats = fields.List(fields.String(), allow_none=True)
    supported_resolutions = fields.List(fields.String(), allow_none=True)
    supported_framerates = fields.List(fields.String(), allow_none=True)
    connection_string = fields.String(allow_none=True, validate=validate.Length(max=500))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    ip_address = fields.String(allow_none=True, validate=validate.Length(max=45))
    port = fields.Integer(allow_none=True)
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    version = fields.String(allow_none=True, validate=validate.Length(max=50))
    serial_number = fields.String(allow_none=True, validate=validate.Length(max=100))
    last_used_at = fields.DateTime(dump_only=True)
    usage_count = fields.Integer(dump_only=True)
    total_recording_time = fields.Float(dump_only=True)
    default_settings = fields.Dict(allow_none=True)
    current_settings = fields.Dict(allow_none=True)
    last_error = fields.String(allow_none=True)
    error_count = fields.Integer(dump_only=True)
    last_error_at = fields.DateTime(dump_only=True)
    user_id = fields.Integer(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    def get_device_type(self, obj):
        """Get device type as string value"""
        if hasattr(obj, 'device_type') and obj.device_type:
            if isinstance(obj.device_type, DeviceType):
                return obj.device_type.value
            return str(obj.device_type)
        return None
    
    def get_status(self, obj):
        """Get status as string value"""
        if hasattr(obj, 'status') and obj.status:
            if isinstance(obj.status, DeviceStatus):
                return obj.status.value
            return str(obj.status)
        return None

class DeviceCreateSchema(Schema):
    """Schema for device creation validation"""
    device_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    device_type = fields.String(required=True, validate=validate.OneOf(['webcam', 'screen', 'rtsp', 'audio', 'file']))
    connection_string = fields.String(allow_none=True, validate=validate.Length(max=500))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    ip_address = fields.String(allow_none=True, validate=validate.Length(max=45))
    port = fields.Integer(allow_none=True)
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    version = fields.String(allow_none=True, validate=validate.Length(max=50))
    serial_number = fields.String(allow_none=True, validate=validate.Length(max=100))
    driver = fields.String(allow_none=True, validate=validate.Length(max=100))
    capabilities = fields.Dict(allow_none=True)
    supported_formats = fields.List(fields.String(), allow_none=True)
    supported_resolutions = fields.List(fields.String(), allow_none=True)
    supported_framerates = fields.List(fields.String(), allow_none=True)
    default_settings = fields.Dict(allow_none=True)
    current_settings = fields.Dict(allow_none=True)
    user_id = fields.Integer(allow_none=True)

class DeviceUpdateSchema(Schema):
    """Schema for device update validation"""
    name = fields.String(validate=validate.Length(min=1, max=255))
    device_type = fields.String(validate=validate.OneOf(['webcam', 'screen', 'rtsp', 'audio', 'file']))
    status = fields.String(validate=validate.OneOf(['available', 'in_use', 'unavailable', 'error']))
    connection_string = fields.String(allow_none=True, validate=validate.Length(max=500))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    ip_address = fields.String(allow_none=True, validate=validate.Length(max=45))
    port = fields.Integer(allow_none=True)
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    version = fields.String(allow_none=True, validate=validate.Length(max=50))
    serial_number = fields.String(allow_none=True, validate=validate.Length(max=100))
    driver = fields.String(allow_none=True, validate=validate.Length(max=100))
    capabilities = fields.Dict(allow_none=True)
    supported_formats = fields.List(fields.String(), allow_none=True)
    supported_resolutions = fields.List(fields.String(), allow_none=True)
    supported_framerates = fields.List(fields.String(), allow_none=True)
    default_settings = fields.Dict(allow_none=True)
    current_settings = fields.Dict(allow_none=True)
    user_id = fields.Integer(allow_none=True)