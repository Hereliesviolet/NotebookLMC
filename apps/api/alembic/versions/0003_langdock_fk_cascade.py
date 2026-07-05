"""langdock_requests.notebook_id / job_id -> ON DELETE CASCADE

Same rationale as 0002: langdock_requests is a best-effort audit trail
(app/chat/service.py::_log_langdock_request), not a record that should ever
block deleting the notebook or job it refers to.

Revision ID: 0003_langdock_fk_cascade
Revises: 0002_jobs_fk_cascade
Create Date: 2026-07-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_langdock_fk_cascade"
down_revision: Union[str, None] = "0002_jobs_fk_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("langdock_requests_notebook_id_fkey", "langdock_requests", type_="foreignkey")
    op.create_foreign_key(
        "langdock_requests_notebook_id_fkey",
        "langdock_requests",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("langdock_requests_job_id_fkey", "langdock_requests", type_="foreignkey")
    op.create_foreign_key(
        "langdock_requests_job_id_fkey",
        "langdock_requests",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("langdock_requests_job_id_fkey", "langdock_requests", type_="foreignkey")
    op.create_foreign_key("langdock_requests_job_id_fkey", "langdock_requests", "jobs", ["job_id"], ["id"])
    op.drop_constraint("langdock_requests_notebook_id_fkey", "langdock_requests", type_="foreignkey")
    op.create_foreign_key(
        "langdock_requests_notebook_id_fkey", "langdock_requests", "notebooks", ["notebook_id"], ["id"]
    )
