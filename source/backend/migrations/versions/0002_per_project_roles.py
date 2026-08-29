"""Per-project roles: add project_members, backfill it, drop users.role.

Implements the schema half of D7 / DEC-009.

Backfill policy — read this before running against real data
------------------------------------------------------------
Before this change there was no project-scoped authorisation at all: any
authenticated user could read and mutate any task in any project (D6 RISK-03).
The faithful translation of that state is therefore that **every existing user
becomes a member of every existing project**, because that is the access they
already had. A migration should not silently revoke access people are relying
on; tightening the roster is a deliberate follow-up action, not a side effect of
an upgrade.

Role assignment on backfill:
  * the project's ``owner_id``            -> PM of that project
  * any user whose old global role was PM -> PM of every project
  * everyone else                         -> MEMBER of every project

**After upgrading, review each project's roster and remove members who should
not be there.** Every project is guaranteed at least one PM: if a project has no
owner and no global PM existed, the lowest-id user is promoted so the project is
never left unadministered.

Revision ID: 0002_per_project_roles
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_per_project_roles"
down_revision = "0001_initial_schema"
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



PROJECT_ROLE_ENUM = sa.Enum("PM", "MEMBER", name="projectroleenum")


def upgrade() -> None:
    bind = op.get_bind()

    _create_enum(PROJECT_ROLE_ENUM, bind)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", PROJECT_ROLE_ENUM, nullable=False, server_default="MEMBER"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_index("ix_project_members_id", "project_members", ["id"])
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    # ---- backfill -------------------------------------------------------
    users = bind.execute(sa.text("SELECT id, role FROM users ORDER BY id")).fetchall()
    projects = bind.execute(sa.text("SELECT id, owner_id FROM projects")).fetchall()

    if users and projects:
        global_pm_ids = {u.id for u in users if (u.role or "MEMBER") == "PM"}
        fallback_user_id = users[0].id

        rows = []
        for project in projects:
            pm_ids = set(global_pm_ids)
            if project.owner_id is not None:
                pm_ids.add(project.owner_id)
            if not pm_ids:
                # Never leave a project without an administrator.
                pm_ids = {fallback_user_id}

            for user in users:
                rows.append({
                    "project_id": project.id,
                    "user_id": user.id,
                    "role": "PM" if user.id in pm_ids else "MEMBER",
                })

        if rows:
            op.bulk_insert(
                sa.table(
                    "project_members",
                    sa.column("project_id", sa.Integer),
                    sa.column("user_id", sa.Integer),
                    sa.column("role", sa.String),
                ),
                rows,
            )

    # ---- drop the global role -------------------------------------------
    # batch_alter_table rebuilds the table on SQLite, which cannot DROP COLUMN
    # on older versions; it is a no-op wrapper elsewhere.
    with op.batch_alter_table("users") as batch:
        batch.drop_column("role")


def downgrade() -> None:
    """
    Restore the global role column, deriving each user's value from their
    memberships: PM anywhere becomes a global PM.
    """
    bind = op.get_bind()

    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("role", sa.String(length=20), nullable=False, server_default="MEMBER")
        )

    bind.execute(sa.text(
        "UPDATE users SET role = 'PM' "
        "WHERE id IN (SELECT user_id FROM project_members WHERE role = 'PM')"
    ))

    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_index("ix_project_members_id", table_name="project_members")
    op.drop_table("project_members")

    _drop_enum(PROJECT_ROLE_ENUM, bind)
