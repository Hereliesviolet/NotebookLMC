"""drop notebook_members - unused sharing scaffolding, never referenced by
any router/service outside the model definition itself (see docs/security.md,
`assert_can_access()` only ever checked `owner_id`). Removed before public
release for consistency with the earlier removal of the dead worker-side
`summaries` package.

Revision ID: 0006_drop_notebook_members
Revises: 0005_users_password_hash
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_drop_notebook_members"
down_revision: Union[str, None] = "0005_users_password_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("notebook_members")


def downgrade() -> None:
    op.create_table(
        "notebook_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
