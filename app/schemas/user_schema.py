from marshmallow import Schema, fields, validate

class UserSchema(Schema):
    """User schema for validation and serialization"""
    id = fields.Integer(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6), load_only=True)
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class UserUpdateSchema(Schema):
    """User update schema for partial updates"""
    username = fields.String(validate=validate.Length(min=3, max=80))
    email = fields.Email()
    password = fields.String(validate=validate.Length(min=6), load_only=True)
    is_active = fields.Boolean()
