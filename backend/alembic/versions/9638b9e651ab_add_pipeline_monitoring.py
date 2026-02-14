"""Add pipeline monitoring tables

Revision ID: add_pipeline_monitoring
Revises: 80af9f6500bd
Create Date: 2026-02-14 19:43:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.core.config import settings

# revision identifiers, used by Alembic.
revision = 'add_pipeline_monitoring'
down_revision = '80af9f6500bd'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Ensure schema exists (for local dev)
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}")

    # Rename admin_jobs table to pipelines
    op.rename_table('admin_jobs', 'pipelines', schema=settings.DB_SCHEMA)
    
    # Rename primary key column
    op.alter_column('pipelines', 'job_id', new_column_name='pipeline_id', schema=settings.DB_SCHEMA)
    
    # Add new columns to pipelines table
    op.add_column('pipelines', sa.Column('pipeline_type', sa.String(50), nullable=True), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('name', sa.String(200), nullable=True), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('description', sa.Text(), nullable=True), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('failed_photos', sa.Integer(), server_default='0'), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('skipped_photos', sa.Integer(), server_default='0'), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('avg_processing_time_ms', sa.Integer(), nullable=True), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('total_processing_time_ms', sa.BigInteger(), server_default='0'), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('cancelled_at', sa.TIMESTAMP(timezone=True), nullable=True), schema=settings.DB_SCHEMA)
    op.add_column('pipelines', sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True), schema=settings.DB_SCHEMA)
    
    # Rename progress columns
    op.alter_column('pipelines', 'progress_total', new_column_name='total_photos', schema=settings.DB_SCHEMA)
    op.alter_column('pipelines', 'progress_current', new_column_name='completed_photos', schema=settings.DB_SCHEMA)
    
    # Migrate existing data - set pipeline_type based on job_type
    op.execute(f"""
        UPDATE {settings.DB_SCHEMA}.pipelines 
        SET pipeline_type = CASE 
            WHEN job_type = 'cluster' THEN 'admin_cluster'
            WHEN job_type = 'rescan' THEN 'admin_rescan'
            ELSE 'admin_' || job_type
        END
        WHERE pipeline_type IS NULL
    """)
    
    # Make pipeline_type NOT NULL after migration
    op.alter_column('pipelines', 'pipeline_type', nullable=False, schema=settings.DB_SCHEMA)
    
    # Drop old indexes
    op.drop_index('idx_admin_jobs_status', table_name='pipelines', schema=settings.DB_SCHEMA)
    op.drop_index('idx_admin_jobs_created', table_name='pipelines', schema=settings.DB_SCHEMA)
    
    # Create new indexes for pipelines
    op.create_index('idx_pipelines_user_status', 'pipelines', ['user_id', 'status'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipelines_status', 'pipelines', ['status'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipelines_created', 'pipelines', ['created_at'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipelines_type', 'pipelines', ['pipeline_type'], schema=settings.DB_SCHEMA)
    
    # Create pipeline_tasks table
    op.create_table(
        'pipeline_tasks',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('photo_filename', sa.String(500), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        
        # Performance metrics
        sa.Column('total_time_ms', sa.Integer(), nullable=True),
        sa.Column('download_time_ms', sa.Integer(), nullable=True),
        sa.Column('thumbnail_time_ms', sa.Integer(), nullable=True),
        sa.Column('face_detection_time_ms', sa.Integer(), nullable=True),
        sa.Column('animal_detection_time_ms', sa.Integer(), nullable=True),
        sa.Column('classification_time_ms', sa.Integer(), nullable=True),
        sa.Column('ocr_time_ms', sa.Integer(), nullable=True),
        sa.Column('db_write_time_ms', sa.Integer(), nullable=True),
        
        # Component results
        sa.Column('faces_detected', sa.Integer(), server_default='0'),
        sa.Column('animals_detected', sa.Integer(), server_default='0'),
        sa.Column('tags_created', sa.Integer(), server_default='0'),
        sa.Column('text_words_extracted', sa.Integer(), server_default='0'),
        
        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        
        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['pipeline_id'], [f'{settings.DB_SCHEMA}.pipelines.pipeline_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['photo_id'], [f'{settings.DB_SCHEMA}.photos.photo_id'], ondelete='CASCADE'),
        
        schema=settings.DB_SCHEMA
    )
    
    # Create indexes for pipeline_tasks
    op.create_index('idx_pipeline_tasks_pipeline', 'pipeline_tasks', ['pipeline_id'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipeline_tasks_status', 'pipeline_tasks', ['pipeline_id', 'status'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipeline_tasks_photo', 'pipeline_tasks', ['photo_id'], schema=settings.DB_SCHEMA)
    op.create_index('idx_pipeline_tasks_celery', 'pipeline_tasks', ['celery_task_id'], schema=settings.DB_SCHEMA)


def downgrade():
    # Drop pipeline_tasks table
    op.drop_index('idx_pipeline_tasks_celery', table_name='pipeline_tasks', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipeline_tasks_photo', table_name='pipeline_tasks', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipeline_tasks_status', table_name='pipeline_tasks', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipeline_tasks_pipeline', table_name='pipeline_tasks', schema=settings.DB_SCHEMA)
    op.drop_table('pipeline_tasks', schema=settings.DB_SCHEMA)
    
    # Drop new indexes
    op.drop_index('idx_pipelines_type', table_name='pipelines', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipelines_created', table_name='pipelines', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipelines_status', table_name='pipelines', schema=settings.DB_SCHEMA)
    op.drop_index('idx_pipelines_user_status', table_name='pipelines', schema=settings.DB_SCHEMA)
    
    # Rename columns back
    op.alter_column('pipelines', 'total_photos', new_column_name='progress_total', schema=settings.DB_SCHEMA)
    op.alter_column('pipelines', 'completed_photos', new_column_name='progress_current', schema=settings.DB_SCHEMA)
    
    # Drop new columns
    op.drop_column('pipelines', 'config', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'cancelled_at', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'total_processing_time_ms', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'avg_processing_time_ms', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'skipped_photos', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'failed_photos', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'description', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'name', schema=settings.DB_SCHEMA)
    op.drop_column('pipelines', 'pipeline_type', schema=settings.DB_SCHEMA)
    
    # Rename primary key back
    op.alter_column('pipelines', 'pipeline_id', new_column_name='job_id', schema=settings.DB_SCHEMA)
    
    # Rename table back
    op.rename_table('pipelines', 'admin_jobs', schema=settings.DB_SCHEMA)
    
    # Recreate old indexes
    op.create_index('idx_admin_jobs_created', 'admin_jobs', ['created_at'], schema=settings.DB_SCHEMA)
    op.create_index('idx_admin_jobs_status', 'admin_jobs', ['status'], schema=settings.DB_SCHEMA)
