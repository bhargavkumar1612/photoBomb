"""Add index for storage provider

Revision ID: 952a81828744
Revises: d155956ea46f
Create Date: 2026-01-24 21:21:17.326234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '952a81828744'
down_revision = 'd155956ea46f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_photos_user_provider_taken', 'photos', ['user_id', 'storage_provider', 'taken_at'], unique=False, schema='photobomb', postgresql_where='deleted_at IS NULL')


def downgrade() -> None:
    op.drop_index('idx_photos_user_provider_taken', table_name='photos', schema='photobomb', postgresql_where='deleted_at IS NULL')
