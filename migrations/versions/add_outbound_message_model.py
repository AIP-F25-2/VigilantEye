"""Add OutboundMessage model for Telegram integration

Revision ID: add_outbound_message_model
Revises: 9b31b496ba4f
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_outbound_message_model'
down_revision = '9b31b496ba4f'
branch_labels = None
depends_on = None


def upgrade():
    # Create outbound_messages table
    op.create_table('outbound_messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('source_type', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('source_channel', sa.String(length=64), nullable=True),
    sa.Column('telegram_chat_id', sa.String(length=64), nullable=True),
    sa.Column('telegram_message_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('initiated', 'sent', 'acknowledged', 'escalated', 'closed', name='messagestatus'), nullable=False),
    sa.Column('meta', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('outbound_messages')
