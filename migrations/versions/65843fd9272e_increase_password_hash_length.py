"""Increase password hash length

Revision ID: 65843fd9272e
Revises: add_face_identity_agent_models
Create Date: 2025-11-07 17:31:00.872209

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '65843fd9272e'
down_revision = 'add_face_identity_agent_models'
branch_labels = None
depends_on = None
def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=255),
            type_=sa.String(length=512),
            existing_nullable=True
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=512),
            type_=sa.String(length=255),
            existing_nullable=True
        )