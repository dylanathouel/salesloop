"""training chunks + pgvector extension

Revision ID: a1c4e9f2b3d7
Revises: 75d82ff9bc41
Create Date: 2026-06-12 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "a1c4e9f2b3d7"
down_revision: str | None = "75d82ff9bc41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "training_chunk",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("training_content_id", sa.UUID(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        # Dimension-less vector: the embedding model stays configurable
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["training_content_id"],
            ["training_content.id"],
            name=op.f("fk_training_chunk_training_content_id_training_content"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_training_chunk")),
    )
    op.create_index(
        op.f("ix_training_chunk_training_content_id"),
        "training_chunk",
        ["training_content_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_training_chunk_training_content_id"), table_name="training_chunk")
    op.drop_table("training_chunk")
