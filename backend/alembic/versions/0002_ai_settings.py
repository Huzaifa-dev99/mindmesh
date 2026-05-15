"""persist ai settings

Revision ID: 0002_ai_settings
Revises: 0001_initial_schema
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ai_settings"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_configs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("default_model_id", sa.String(length=255), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("models", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_ai_provider_configs_user"),
    )
    op.create_index(op.f("ix_ai_provider_configs_user_id"), "ai_provider_configs", ["user_id"], unique=False)

    op.create_table(
        "chat_model_selections",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "conversation_id", name="uq_chat_model_selection_user_conversation"),
    )
    op.create_index(op.f("ix_chat_model_selections_conversation_id"), "chat_model_selections", ["conversation_id"], unique=False)
    op.create_index("ix_chat_model_selection_user_conversation", "chat_model_selections", ["user_id", "conversation_id"], unique=False)
    op.create_index(op.f("ix_chat_model_selections_user_id"), "chat_model_selections", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_model_selections_user_id"), table_name="chat_model_selections")
    op.drop_index("ix_chat_model_selection_user_conversation", table_name="chat_model_selections")
    op.drop_index(op.f("ix_chat_model_selections_conversation_id"), table_name="chat_model_selections")
    op.drop_table("chat_model_selections")
    op.drop_index(op.f("ix_ai_provider_configs_user_id"), table_name="ai_provider_configs")
    op.drop_table("ai_provider_configs")
