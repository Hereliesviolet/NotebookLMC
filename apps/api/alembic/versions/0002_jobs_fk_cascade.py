"""jobs.source_id / jobs.notebook_id -> ON DELETE CASCADE

Jobs are pure history/status rows; deleting a source or notebook must not
be blocked by them (was previously blocking source deletion with a
ForeignKeyViolationError on jobs_source_id_fkey).

Revision ID: 0002_jobs_fk_cascade
Revises: 0001_initial
Create Date: 2026-07-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_jobs_fk_cascade"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("jobs_source_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key(
        "jobs_source_id_fkey", "jobs", "sources", ["source_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("jobs_notebook_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key(
        "jobs_notebook_id_fkey", "jobs", "notebooks", ["notebook_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("jobs_notebook_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_notebook_id_fkey", "jobs", "notebooks", ["notebook_id"], ["id"])
    op.drop_constraint("jobs_source_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_source_id_fkey", "jobs", "sources", ["source_id"], ["id"])
