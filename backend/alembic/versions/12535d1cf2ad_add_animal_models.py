from alembic import op
import sqlalchemy as sa
from app.core.config import settings
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision = '12535d1cf2ad'
down_revision = 'c492947c346e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Inspection to make migration idempotent
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names(schema=settings.DB_SCHEMA)

    if 'animals' not in tables:
        # Create animals table
        op.create_table(
            'animals',
            sa.Column('animal_id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=True),
            sa.Column('cover_detection_id', sa.UUID(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], [f'{settings.DB_SCHEMA}.users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('animal_id'),
            schema=settings.DB_SCHEMA
        )
    
    if 'animal_detections' not in tables:
        # Create animal_detections table
        op.create_table(
            'animal_detections',
            sa.Column('detection_id', sa.UUID(), nullable=False),
            sa.Column('photo_id', sa.UUID(), nullable=False),
            sa.Column('animal_id', sa.UUID(), nullable=True),
            sa.Column('label', sa.String(length=100), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('embedding', pgvector.sqlalchemy.Vector(512), nullable=True),
            sa.Column('location_top', sa.Integer(), nullable=False),
            sa.Column('location_right', sa.Integer(), nullable=False),
            sa.Column('location_bottom', sa.Integer(), nullable=False),
            sa.Column('location_left', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['animal_id'], [f'{settings.DB_SCHEMA}.animals.animal_id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['photo_id'], [f'{settings.DB_SCHEMA}.photos.photo_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('detection_id'),
            schema=settings.DB_SCHEMA
        )
        
        # Add foreign key for cover_detection_id to animals (cyclic)
        op.create_foreign_key(
            'fk_animals_cover_detection', 'animals', 'animal_detections',
            ['cover_detection_id'], ['detection_id'],
            source_schema=settings.DB_SCHEMA, referent_schema=settings.DB_SCHEMA,
            ondelete='SET NULL', use_alter=True
        )

        # Indexes
        op.create_index('idx_animal_detections_animal', 'animal_detections', ['animal_id'], unique=False, schema=settings.DB_SCHEMA)
        op.create_index('idx_animal_detections_photo', 'animal_detections', ['photo_id'], unique=False, schema=settings.DB_SCHEMA)


def downgrade() -> None:
    op.drop_index('idx_animal_detections_photo', table_name='animal_detections', schema=settings.DB_SCHEMA)
    op.drop_index('idx_animal_detections_animal', table_name='animal_detections', schema=settings.DB_SCHEMA)
    op.drop_constraint('fk_animals_cover_detection', 'animals', schema=settings.DB_SCHEMA)
    op.drop_table('animal_detections', schema=settings.DB_SCHEMA)
    op.drop_table('animals', schema=settings.DB_SCHEMA)
