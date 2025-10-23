from marshmallow import Schema, fields, validate

class DeviceSchema(Schema):
    """Device schema for serialization"""
    id = fields.Integer(dump_only=True)
    device_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    device_type = fields.String(required=True, validate=validate.OneOf(['rtsp', 'usb', 'ip', 'webcam']))
    ip_address = fields.String(required=True, validate=validate.Length(min=1, max=45))
    status = fields.String(dump_only=True)
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class DeviceCreateSchema(Schema):
    """Schema for device creation validation"""
    device_id = fields.String(required=True, validate=validate.Length(min=1, max=100))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    device_type = fields.String(required=True, validate=validate.OneOf(['rtsp', 'usb', 'ip', 'webcam']))
    ip_address = fields.String(required=True, validate=validate.Length(min=1, max=45))
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))

class DeviceUpdateSchema(Schema):
    """Schema for device update validation"""
    name = fields.String(validate=validate.Length(min=1, max=255))
    device_type = fields.String(validate=validate.OneOf(['rtsp', 'usb', 'ip', 'webcam']))
    ip_address = fields.String(validate=validate.Length(min=1, max=45))
    status = fields.String(validate=validate.OneOf(['available', 'recording', 'offline', 'error']))
    manufacturer = fields.String(allow_none=True, validate=validate.Length(max=100))
    model = fields.String(allow_none=True, validate=validate.Length(max=100))
    rtsp_url = fields.String(allow_none=True, validate=validate.Length(max=500))