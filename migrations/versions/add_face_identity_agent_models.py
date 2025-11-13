"""Add Face & Identity Agent models for CCTV processing

Revision ID: add_face_identity_agent_models
Revises: add_faceai_models
Create Date: 2025-01-15 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_face_identity_agent_models'
down_revision = 'add_faceai_models'
branch_labels = None
depends_on = None

def upgrade():
    # Create person_identities table for tracking persons across cameras
    op.create_table('person_identities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('person_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('person_type', sa.Enum('employee', 'vip', 'suspect', 'unknown', 'visitor', name='persontype'), nullable=False),
        sa.Column('face_encoding', sa.JSON(), nullable=True),
        sa.Column('demographics', sa.JSON(), nullable=True),
        sa.Column('disguise_detected', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cameras_seen', sa.JSON(), nullable=True),
        sa.Column('watchlist_status', sa.Boolean(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id')
    )

    # Create watchlist_members table for watchlist management
    op.create_table('watchlist_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('person_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('person_type', sa.Enum('employee', 'vip', 'suspect', name='watchlisttype'), nullable=False),
        sa.Column('face_encoding', sa.JSON(), nullable=False),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('added_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id')
    )

    # Create cctv_processing_jobs table for tracking video processing
    op.create_table('cctv_processing_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=False),
        sa.Column('camera_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='jobstatus'), nullable=False),
        sa.Column('frames_processed', sa.Integer(), nullable=True),
        sa.Column('faces_detected', sa.Integer(), nullable=True),
        sa.Column('unique_persons', sa.Integer(), nullable=True),
        sa.Column('watchlist_matches', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create camera_status table for tracking camera activity
    op.create_table('camera_status',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('camera_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'error', 'maintenance', name='camerastatus'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('persons_detected', sa.Integer(), nullable=True),
        sa.Column('watchlist_alerts', sa.Integer(), nullable=True),
        sa.Column('processing_fps', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('camera_id')
    )

    # Create disguise_detections table for tracking disguise analysis
    op.create_table('disguise_detections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('face_detection_id', sa.String(length=36), nullable=True),
        sa.Column('person_id', sa.String(length=100), nullable=True),
        sa.Column('disguise_types', sa.JSON(), nullable=False),
        sa.Column('confidence_scores', sa.JSON(), nullable=True),
        sa.Column('detection_method', sa.String(length=50), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['face_detection_id'], ['face_detections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cross_age_comparisons table for tracking cross-age recognition
    op.create_table('cross_age_comparisons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('person_id_1', sa.String(length=100), nullable=False),
        sa.Column('person_id_2', sa.String(length=100), nullable=False),
        sa.Column('age_group_1', sa.String(length=20), nullable=True),
        sa.Column('age_group_2', sa.String(length=20), nullable=True),
        sa.Column('face_similarity', sa.Float(), nullable=False),
        sa.Column('age_similarity', sa.Float(), nullable=True),
        sa.Column('combined_similarity', sa.Float(), nullable=False),
        sa.Column('is_same_person', sa.Boolean(), nullable=False),
        sa.Column('confidence_threshold', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes for better performance
    op.create_index('idx_person_identities_person_id', 'person_identities', ['person_id'])
    op.create_index('idx_person_identities_person_type', 'person_identities', ['person_type'])
    op.create_index('idx_person_identities_last_seen', 'person_identities', ['last_seen'])
    op.create_index('idx_watchlist_members_person_type', 'watchlist_members', ['person_type'])
    op.create_index('idx_watchlist_members_is_active', 'watchlist_members', ['is_active'])
    op.create_index('idx_cctv_processing_jobs_status', 'cctv_processing_jobs', ['status'])
    op.create_index('idx_cctv_processing_jobs_camera_id', 'cctv_processing_jobs', ['camera_id'])
    op.create_index('idx_camera_status_camera_id', 'camera_status', ['camera_id'])
    op.create_index('idx_camera_status_status', 'camera_status', ['status'])
    op.create_index('idx_disguise_detections_person_id', 'disguise_detections', ['person_id'])
    op.create_index('idx_cross_age_comparisons_person_ids', 'cross_age_comparisons', ['person_id_1', 'person_id_2'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_cross_age_comparisons_person_ids', 'cross_age_comparisons')
    op.drop_index('idx_disguise_detections_person_id', 'disguise_detections')
    op.drop_index('idx_camera_status_status', 'camera_status')
    op.drop_index('idx_camera_status_camera_id', 'camera_status')
    op.drop_index('idx_cctv_processing_jobs_camera_id', 'cctv_processing_jobs')
    op.drop_index('idx_cctv_processing_jobs_status', 'cctv_processing_jobs')
    op.drop_index('idx_watchlist_members_is_active', 'watchlist_members')
    op.drop_index('idx_watchlist_members_person_type', 'watchlist_members')
    op.drop_index('idx_person_identities_last_seen', 'person_identities')
    op.drop_index('idx_person_identities_person_type', 'person_identities')
    op.drop_index('idx_person_identities_person_id', 'person_identities')

    # Drop tables
    op.drop_table('cross_age_comparisons')
    op.drop_table('disguise_detections')
    op.drop_table('camera_status')
    op.drop_table('cctv_processing_jobs')
    op.drop_table('watchlist_members')
    op.drop_table('person_identities')

