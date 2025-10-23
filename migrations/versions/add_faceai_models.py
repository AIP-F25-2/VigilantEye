"""Add FaceAi models for face detection and analysis

Revision ID: add_faceai_models
Revises: add_outbound_message_model
Create Date: 2025-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_faceai_models'
down_revision = 'add_outbound_message_model'
branch_labels = None
depends_on = None

def upgrade():
    # Create face_detections table
    op.create_table('face_detections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_path', sa.String(length=500), nullable=True),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('frame_number', sa.Integer(), nullable=True),
        sa.Column('faces_detected', sa.Integer(), nullable=True),
        sa.Column('detection_results', sa.JSON(), nullable=True),
        sa.Column('annotated_image_path', sa.String(length=500), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('confidence_threshold', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create demographics_analyses table
    op.create_table('demographics_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('face_detection_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('source_path', sa.String(length=500), nullable=True),
        sa.Column('faces_analyzed', sa.Integer(), nullable=True),
        sa.Column('analysis_results', sa.JSON(), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['face_detection_id'], ['face_detections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ambiguity_analyses table
    op.create_table('ambiguity_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('image1_path', sa.String(length=500), nullable=False),
        sa.Column('image2_path', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=True),
        sa.Column('is_ambiguous', sa.Boolean(), nullable=True),
        sa.Column('ambiguity_score', sa.Float(), nullable=False),
        sa.Column('similarity_scores', sa.JSON(), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('weights', sa.JSON(), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('threshold_used', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create face_encodings table
    op.create_table('face_encodings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('person_id', sa.String(length=100), nullable=False),
        sa.Column('face_detection_id', sa.String(length=36), nullable=True),
        sa.Column('source_path', sa.String(length=500), nullable=True),
        sa.Column('face_encoding', sa.JSON(), nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('similarity_threshold', sa.Float(), nullable=True),
        sa.Column('is_known_person', sa.Boolean(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['face_detection_id'], ['face_detections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create faceai_configurations table
    op.create_table('faceai_configurations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('config_name', sa.String(length=100), nullable=False),
        sa.Column('config_data', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_name')
    )

def downgrade():
    op.drop_table('faceai_configurations')
    op.drop_table('face_encodings')
    op.drop_table('ambiguity_analyses')
    op.drop_table('demographics_analyses')
    op.drop_table('face_detections')
