"""Fix password_hash column length

Revision ID: fix_password_hash
Revises: 9b31b496ba4f
Create Date: 2025-10-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_password_hash'
down_revision = '9b31b496ba4f'
branch_labels = None
depends_on = None


def upgrade():
    # Increase password_hash column length from 128 to 255
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=128),
                              type_=sa.String(length=255),
                              existing_nullable=True)


def downgrade():
    # Revert password_hash column length back to 128
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
                              existing_type=sa.String(length=255),
                              type_=sa.String(length=128),
                              existing_nullable=True)
