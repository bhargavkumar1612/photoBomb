"""Add storage_provider to photos

Revision ID: d155956ea46f
Revises: fc167775b497
Create Date: 2026-01-24 20:10:42.529269

"""
from alembic import op
from app.core.config import settings
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd155956ea46f'
down_revision = 'fc167775b497'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Inspection to make migration idempotent
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('photos', schema=settings.DB_SCHEMA)]

    if 'storage_provider' not in columns:
        op.add_column('photos', sa.Column('storage_provider', sa.String(length=20), nullable=False, server_default='b2_native'), schema=settings.DB_SCHEMA)


def downgrade() -> None:
    op.drop_column('photos', 'storage_provider', schema=settings.DB_SCHEMA)
