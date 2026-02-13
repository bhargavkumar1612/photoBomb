"""Create admin_jobs table

Revision ID: add_admin_jobs
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

def upgrade():
    op.create_table(
        'admin_jobs',
        sa.Column('job_id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('production.users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_type', sa.String(50), nullable=False),  # 'faces', 'animals', 'hashtags'
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # pending, running, completed, failed
        sa.Column('target_user_ids', sa.JSON, nullable=False),  # List of user IDs to process
        sa.Column('scopes', sa.JSON, nullable=False),  # List of scopes (faces, animals, hashtags)
        sa.Column('force_reset', sa.Boolean, default=False),
        sa.Column('progress_current', sa.Integer, default=0),
        sa.Column('progress_total', sa.Integer, default=0),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        schema='production'
    )
    
    op.create_index('idx_admin_jobs_status', 'admin_jobs', ['status'], schema='production')
    op.create_index('idx_admin_jobs_created', 'admin_jobs', ['created_at'], schema='production')

def downgrade():
    op.drop_index('idx_admin_jobs_created', table_name='admin_jobs', schema='production')
    op.drop_index('idx_admin_jobs_status', table_name='admin_jobs', schema='production')
    op.drop_table('admin_jobs', schema='production')
