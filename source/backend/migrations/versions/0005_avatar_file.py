"""Store the on-disk name of an uploaded avatar.

`users.avatar_url` already existed and held whatever a Google sign-in returned.
Uploads need a second field: the served URL carries a cache-busting segment, so
it cannot double as the filesystem name without the two meanings drifting.

Revision ID: 0005_avatar_file
Revises: 0004_multi_assignee_and_evidence
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_avatar_file"
down_revision = "0004_multi_assignee_and_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("avatar_file", sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Also clear avatar_url where it pointed at an uploaded file: without
    # avatar_file the serve route cannot find the bytes, so the URL would render
    # as a broken image rather than falling back to initials. A Google avatar is
    # an absolute URL and is left alone.
    op.execute("UPDATE users SET avatar_url = NULL WHERE avatar_url LIKE '/api/users/%'")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("avatar_file")
