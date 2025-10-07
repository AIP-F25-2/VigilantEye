from marshmallow import Schema, fields, validate

class LoginSchema(Schema):
    """Schema for user login validation"""
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6))

class RegisterSchema(Schema):
    """Schema for user registration validation"""
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6))
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    roles = fields.List(fields.String(), missing=["operator"])
    site_id = fields.String(missing="default", validate=validate.Length(max=100))

class TokenResponseSchema(Schema):
    """Schema for token response"""
    access_token = fields.String()
    refresh_token = fields.String()
    user = fields.Dict()

class UserResponseSchema(Schema):
    """Schema for user response"""
    id = fields.Integer()
    email = fields.Email()
    username = fields.String()
    roles = fields.List(fields.String())
    site_id = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
