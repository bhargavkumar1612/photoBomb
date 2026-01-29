"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-10 22:50:00

"""
from alembic import op
from app.core.config import settings
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create photobomb schema
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"')
    
    # Install extensions (in public schema for shared use)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gin')
    
    # Users table (in photobomb schema)
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('google_id', sa.String(255), unique=True, nullable=True),
        sa.Column('apple_id', sa.String(255), unique=True, nullable=True),
        sa.Column('face_recognition_enabled', sa.Boolean(), default=False),
        sa.Column('storage_quota_bytes', sa.BigInteger(), default=107374182400),
        sa.Column('storage_used_bytes', sa.BigInteger(), default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'", name='email_format'),
        schema=settings.DB_SCHEMA
    )
    
    # Photos table (in photobomb schema)
    op.create_table(
        'photos',
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey(f'{settings.DB_SCHEMA}.users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False, index=True),
        sa.Column('phash', sa.BigInteger(), nullable=True, index=True),
        sa.Column('taken_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('camera_make', sa.String(100), nullable=True),
        sa.Column('camera_model', sa.String(100), nullable=True),
        sa.Column('lens', sa.String(100), nullable=True),
        sa.Column('iso', sa.Integer(), nullable=True),
        sa.Column('aperture', sa.String(20), nullable=True),
        sa.Column('shutter_speed', sa.String(20), nullable=True),
        sa.Column('focal_length', sa.String(20), nullable=True),
        sa.Column('gps_lat', sa.Numeric(10, 7), nullable=True),
        sa.Column('gps_lng', sa.Numeric(10, 7), nullable=True),
        sa.Column('gps_altitude', sa.Numeric(8, 2), nullable=True),
        sa.Column('location_name', sa.Text(), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('favorite', sa.Boolean(), default=False),
        sa.Column('archived', sa.Boolean(), default=False),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/heic', 'image/webp', 'image/avif')", name='valid_mime_type'),
        schema=settings.DB_SCHEMA
    )
    
    # Indexes for photos
    op.create_index('idx_photos_user_taken', 'photos', ['user_id', 'taken_at'], 
                    postgresql_where=sa.text('deleted_at IS NULL'),
                    schema=settings.DB_SCHEMA)
    op.create_index('idx_photos_user_uploaded', 'photos', ['user_id', 'uploaded_at'], 
                    postgresql_where=sa.text('deleted_at IS NULL'),
                    schema=settings.DB_SCHEMA)
    op.create_index('idx_photos_favorite', 'photos', ['user_id', 'uploaded_at'], 
                    postgresql_where=sa.text('favorite = true AND deleted_at IS NULL'),
                    schema=settings.DB_SCHEMA)
    
    # Photo files table (in photobomb schema)
    op.create_table(
        'photo_files',
        sa.Column('file_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey(f'{settings.DB_SCHEMA}.photos.photo_id', ondelete='CASCADE'), nullable=False),
        sa.Column('variant', sa.String(50), nullable=False),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('storage_backend', sa.String(20), default='b2'),
        sa.Column('b2_bucket', sa.String(100), nullable=True),
        sa.Column('b2_key', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        schema=settings.DB_SCHEMA
    )
    
    op.create_index('idx_photo_files_photo', 'photo_files', ['photo_id'], schema=settings.DB_SCHEMA)
    op.create_index('idx_photo_files_unique', 'photo_files', ['photo_id', 'variant', 'format'], unique=True, schema=settings.DB_SCHEMA)


def downgrade() -> None:
    # Drop tables (will cascade due to schema drop, but being explicit)
    op.drop_table('photo_files', schema=settings.DB_SCHEMA)
    op.drop_table('photos', schema=settings.DB_SCHEMA)
    op.drop_table('users', schema=settings.DB_SCHEMA)
    
    # Drop schema
    op.execute(f'DROP SCHEMA IF EXISTS "{settings.DB_SCHEMA}" CASCADE')
    
    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS vector')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS btree_gin')
