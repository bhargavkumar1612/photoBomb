"""add index for person photo count

Revision ID: c492947c346e
Revises: 0a57f3bd43de
Create Date: 2026-01-30 01:06:02.554846

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c492947c346e'
down_revision = '0a57f3bd43de'
branch_labels = None
depends_on = None


from app.core.config import settings

def upgrade() -> None:
    try:
        op.create_index('ix_faces_person_photo', 'faces', ['person_id', 'photo_id'], unique=False, schema=settings.DB_SCHEMA)
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index('ix_faces_person_photo', table_name='faces', schema=settings.DB_SCHEMA)
