"""Add is_admin to users

Revision ID: f345dc32710b
Revises: 833cad635c49
Create Date: 2026-02-04 23:53:34.426959

"""
from alembic import op
import sqlalchemy as sa
from app.core.config import settings


# revision identifiers, used by Alembic.
revision = 'f345dc32710b'
down_revision = '833cad635c49'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only add the is_admin column - skip all the index renaming
    # The index renaming was auto-generated noise and not actually needed
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True), schema=settings.DB_SCHEMA)


def downgrade() -> None:
    op.drop_column('users', 'is_admin', schema=settings.DB_SCHEMA)
