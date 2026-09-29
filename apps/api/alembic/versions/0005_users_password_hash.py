"""users.password_hash - real email/password auth (replaces the dev/demo
static-token stub, see docs/security.md).

Two-step add (nullable -> backfill -> NOT NULL) instead of a direct NOT
NULL column: this repo may already have rows in `users` (demo/test users
seeded before this migration) with no password at all. Backfilling with a
hash of a random, never-revealed placeholder value locks those accounts out
(they didn't have real credentials to begin with) while keeping the
migration safe to run against both an empty and an already-populated `users`
table.

Revision ID: 0005_users_password_hash
Revises: 0004_studio_artifacts
Create Date: 2026-07-06
"""

import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from argon2 import PasswordHasher

from alembic import op

revision: str = "0005_users_password_hash"
down_revision: Union[str, None] = "0004_studio_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

    users = sa.table(
        "users",
        sa.column("id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("password_hash", sa.String),
    )
    hasher = PasswordHasher()
    connection = op.get_bind()
    existing_ids = [row.id for row in connection.execute(sa.select(users.c.id))]
    for user_id in existing_ids:
        placeholder_hash = hasher.hash(secrets.token_urlsafe(32))
        connection.execute(
            users.update().where(users.c.id == user_id).values(password_hash=placeholder_hash)
        )

    op.alter_column("users", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
