"""increase_password_hash_to_512

Revision ID: b7f9ca05eb6c
Revises: add_face_identity_agent_models
Create Date: 2025-11-20 16:50:42.354794

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7f9ca05eb6c'
down_revision = 'add_face_identity_agent_models'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=128),
            type_=sa.String(length=512),
            existing_nullable=True
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=512),
            type_=sa.String(length=128),
            existing_nullable=True
        )