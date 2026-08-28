"""Membership invitations: a PM adding someone is a request, not a fact.

Adds `status`, `invited_by_id` and `responded_at` to `project_members`.

Backfill is ACCEPTED for every existing row, and that is the only safe choice:
those people already have access today. Defaulting them to PENDING would lock
every current member out of every project until they happened to notice an
invitation — a data migration that silently revokes access is a far worse
failure than one that grants slightly more than a purist would like.

New rows created by `add_member` are PENDING. The difference between "already a
member" and "newly invited" is therefore drawn at the migration boundary, which
is exactly where it belongs.

Revision ID: 0003_membership_invitations
Revises: 0002_per_project_roles
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_membership_invitations"
down_revision = "0002_per_project_roles"
branch_labels = None
depends_on = None

MEMBERSHIP_STATUS = sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="membershipstatusenum")


def upgrade() -> None:
    bind = op.get_bind()
    MEMBERSHIP_STATUS.create(bind, checkfirst=True)

    # server_default is required: SQLite cannot add a NOT NULL column without
    # one, and existing rows need a value in the same statement.
    with op.batch_alter_table("project_members") as batch:
        batch.add_column(
            sa.Column(
                "status",
                MEMBERSHIP_STATUS,
                nullable=False,
                server_default="ACCEPTED",
            )
        )
        batch.add_column(sa.Column("invited_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("responded_at", sa.DateTime(), nullable=True))

    # Every pre-existing membership is a real one. Explicit rather than relying
    # on the default, so the intent survives being read later.
    op.execute("UPDATE project_members SET status = 'ACCEPTED' WHERE status IS NULL")


def downgrade() -> None:
    # Dropping the column discards the distinction: a pending invitation becomes
    # indistinguishable from an accepted membership, which means downgrading
    # GRANTS ACCESS to everyone who was merely invited. Delete those rows first
    # so the downgrade cannot silently widen access.
    op.execute("DELETE FROM project_members WHERE status IN ('PENDING', 'DECLINED')")

    with op.batch_alter_table("project_members") as batch:
        batch.drop_column("responded_at")
        batch.drop_column("invited_by_id")
        batch.drop_column("status")

    MEMBERSHIP_STATUS.drop(op.get_bind(), checkfirst=True)
