"""Multiple assignees per task; comment kinds; attachments.

Three changes that arrived together because they are one feature: a task is
worked on by people (plural), progress is discussed, and moving it to DONE
should leave proof.

`tasks.assignee_id` becomes the `task_assignees` join table — the same
attributive-to-relational move that 0002 made for roles, for the same reason:
the column could represent exactly one fact, and the fact is not always one.

Backfill copies every existing `assignee_id` into a row, so nobody loses an
assignment. Tasks with no assignee simply get no row.

Revision ID: 0004_multi_assignee_and_evidence
Revises: 0003_membership_invitations
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_multi_assignee_and_evidence"
down_revision = "0003_membership_invitations"
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


def _drop_fks_on(bind, table: str, column: str) -> None:
    """
    Drop any foreign-key constraint covering `column`, by inspection.

    MySQL refuses to drop a column that a foreign key still references
    ("Cannot drop column 'assignee_id': needed in a foreign key constraint"),
    and the constraint's name is auto-generated — `tasks_ibfk_3` here — so it
    cannot be written down portably.

    SQLite reaches this through `batch_alter_table`, which rebuilds the table
    without the column and its constraint in one step, so nothing is needed and
    this is skipped. That gate is also why editing this already-applied
    migration is safe: for every database that has run it (all SQLite), the
    behaviour is unchanged.
    """
    if bind.dialect.name == "sqlite":
        return
    from sqlalchemy import inspect as sa_inspect

    for fk in sa_inspect(bind).get_foreign_keys(table):
        if column in (fk.get("constrained_columns") or []) and fk.get("name"):
            op.drop_constraint(fk["name"], table, type_="foreignkey")



COMMENT_KIND = sa.Enum("COMMENT", "EVIDENCE", name="commentkindenum")


def upgrade() -> None:
    bind = op.get_bind()

    # ---- task_assignees -----------------------------------------------------
    op.create_table(
        "task_assignees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignee"),
    )
    op.create_index("ix_task_assignees_task_id", "task_assignees", ["task_id"])
    op.create_index("ix_task_assignees_user_id", "task_assignees", ["user_id"])

    # Carry every existing assignment across before the column goes. A task
    # whose assignee_id points at a deleted user is skipped rather than
    # violating the foreign key.
    op.execute(
        """
        INSERT INTO task_assignees (task_id, user_id, created_at)
        SELECT t.id, t.assignee_id, CURRENT_TIMESTAMP
        FROM tasks t
        WHERE t.assignee_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM users u WHERE u.id = t.assignee_id)
        """
    )

    _drop_fks_on(bind, "tasks", "assignee_id")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("assignee_id")

    # ---- comment kinds ------------------------------------------------------
    _create_enum(COMMENT_KIND, bind)
    with op.batch_alter_table("comments") as batch:
        batch.add_column(
            sa.Column("kind", COMMENT_KIND, nullable=False, server_default="COMMENT")
        )

    # ---- attachments --------------------------------------------------------
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("uploader_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index("ix_attachments_comment_id", "attachments", ["comment_id"])


def downgrade() -> None:
    # assignee_id can hold one value, so a task with several assignees has to
    # lose all but one. Keep the lowest id — arbitrary, but deterministic, and
    # stated here so nobody believes a downgrade is lossless. Uploaded files on
    # disk are NOT deleted; the rows go and the bytes are orphaned rather than
    # destroyed by a schema operation.
    op.drop_index("ix_attachments_comment_id", table_name="attachments")
    op.drop_table("attachments")

    with op.batch_alter_table("comments") as batch:
        batch.drop_column("kind")
    _drop_enum(COMMENT_KIND, op.get_bind())

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("assignee_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE tasks
        SET assignee_id = (
            SELECT MIN(ta.user_id) FROM task_assignees ta WHERE ta.task_id = tasks.id
        )
        """
    )

    op.drop_index("ix_task_assignees_user_id", table_name="task_assignees")
    op.drop_index("ix_task_assignees_task_id", table_name="task_assignees")
    op.drop_table("task_assignees")
