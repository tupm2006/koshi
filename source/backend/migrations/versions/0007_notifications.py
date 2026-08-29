"""A general notification feed.

Deliberately not "mention notifications". The columns describe *an event
addressed to someone*, with nullable context keys, so later kinds — assignment,
invitation, an approaching due date — need no schema change. The enum is a
plain string column on SQLite, so adding a kind needs no migration either.

Revision ID: 0007_notifications
Revises: 0006_comment_replies
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_notifications"
down_revision = "0006_comment_replies"
branch_labels = None
depends_on = None


def _create_enum(enum_type, bind) -> None:
    """
    Create a standalone enum type where the dialect has one.

    PostgreSQL needs `CREATE TYPE`; MySQL puts the value list inline on the
    column and SQLite stores a VARCHAR, so calling `.create()` on either is at
    best a no-op and at worst an error. `checkfirst` handles re-runs.
    """
    if bind.dialect.name == "postgresql":
        enum_type.create(bind, checkfirst=True)


def _drop_enum(enum_type, bind) -> None:
    if bind.dialect.name == "postgresql":
        enum_type.drop(bind, checkfirst=True)



NOTIFICATION_KIND = sa.Enum(
    "MENTION", "REPLY", "TASK_ASSIGNED", "PROJECT_INVITED", "TASK_DUE_SOON",
    name="notificationkindenum",
)


def upgrade() -> None:
    _create_enum(NOTIFICATION_KIND, op.get_bind())

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", NOTIFICATION_KIND, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        # CASCADE throughout: a notification about a deleted task is not
        # something to keep and then have to filter out on every read.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    # The query behind the unread badge, which runs on every page load.
    op.create_index(
        "ix_notifications_user_unread", "notifications", ["user_id", "read_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_project_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    _drop_enum(NOTIFICATION_KIND, op.get_bind())
