"""add note scope

Revision ID: 0003_note_scope
Revises: 0002_ai_settings
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_note_scope"
down_revision = "0002_ai_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("scope", sa.String(length=20), server_default="global", nullable=False))
    op.add_column("notes", sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_notes_chat_id"), "notes", ["chat_id"], unique=False)
    op.create_foreign_key("fk_notes_chat_id_conversations", "notes", "conversations", ["chat_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_notes_chat_id_conversations", "notes", type_="foreignkey")
    op.drop_index(op.f("ix_notes_chat_id"), table_name="notes")
    op.drop_column("notes", "chat_id")
    op.drop_column("notes", "scope")
