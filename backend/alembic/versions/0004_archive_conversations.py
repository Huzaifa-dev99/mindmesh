"""add conversation archive

Revision ID: 0004_archive_conversations
Revises: 0003_note_scope
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_archive_conversations"
down_revision = "0003_note_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "archived_at")
