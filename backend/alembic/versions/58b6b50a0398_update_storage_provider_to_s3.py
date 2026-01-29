"""update_storage_provider_to_s3

Revision ID: 58b6b50a0398
Revises: 952a81828744
Create Date: 2026-01-29 00:02:42.289719

"""
from alembic import op
from app.core.config import settings
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58b6b50a0398'
down_revision = '952a81828744'
branch_labels = None
depends_on = None




def upgrade() -> None:
    op.execute(f"UPDATE \"{settings.DB_SCHEMA}\".photos SET storage_provider = 's3' WHERE storage_provider = 'b2_native'")
    op.execute(f"UPDATE \"{settings.DB_SCHEMA}\".photo_files SET storage_backend = 's3' WHERE storage_backend = 'b2'")


def downgrade() -> None:
    op.execute(f"UPDATE \"{settings.DB_SCHEMA}\".photos SET storage_provider = 'b2_native' WHERE storage_provider = 's3'")
    op.execute(f"UPDATE \"{settings.DB_SCHEMA}\".photo_files SET storage_backend = 'b2' WHERE storage_backend = 's3'")
