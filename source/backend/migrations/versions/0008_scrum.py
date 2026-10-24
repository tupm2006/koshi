"""Scrum: sprint lifecycle and completion timestamps.

Sprints existed as rows but had no lifecycle — `is_active` was the only state
and nothing ever cleared it. Scrum needs three states (planned, active,
completed), what the team committed to when the sprint started (velocity), and
when each task was finished (burndown).

  tasks.completed_at        set when a task enters DONE, cleared when it leaves
  sprints.completed_at      set when the sprint is closed; NULL = not closed
  sprints.committed_points  story points in the sprint at the moment it started

Backfill: tasks already DONE get completed_at = updated_at, the best evidence
there is. Existing sprints keep is_active as it was.

Revision ID: 0008_scrum
Revises: 0007_notifications
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_scrum"
down_revision = "0007_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("sprints") as batch:
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("committed_points", sa.Integer(), nullable=True))
    op.execute("UPDATE tasks SET completed_at = updated_at WHERE status = 'DONE'")


def downgrade() -> None:
    with op.batch_alter_table("sprints") as batch:
        batch.drop_column("committed_points")
        batch.drop_column("completed_at")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("completed_at")
