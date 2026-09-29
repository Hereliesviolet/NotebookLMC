"""studio_artifacts - Studio MVP2 (summary/faq/timeline/briefing, architecture
doc §19/§26.5). At most one row per (notebook_id, type); "Neu generieren"
upserts via the unique constraint instead of accumulating history rows.

Revision ID: 0004_studio_artifacts
Revises: 0003_langdock_fk_cascade
Create Date: 2026-07-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_studio_artifacts"
down_revision: Union[str, None] = "0003_langdock_fk_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studio_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("source_ids_json", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("notebook_id", "type", name="uq_studio_artifacts_notebook_type"),
    )


def downgrade() -> None:
    op.drop_table("studio_artifacts")
