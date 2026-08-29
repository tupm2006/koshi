"""Replies: a comment may hang off another comment.

One level only. `parent_id` on a reply always points at a top-level comment, so
the tree is at most two deep — enforced in the router, not by the schema, since
SQL cannot express "the parent must not itself have a parent".

Mentions need no schema: they live as `@[Name](id)` tokens inside `content`.
See `services/mentions.py` for why there is deliberately no mentions table.

Revision ID: 0006_comment_replies
Revises: 0005_avatar_file
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_comment_replies"
down_revision = "0005_avatar_file"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("comments") as batch:
        batch.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_comments_parent_id", "comments", ["parent_id"], ["id"], ondelete="CASCADE"
        )
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])


def downgrade() -> None:
    # Replies are kept, not deleted: they are somebody's writing, and losing the
    # nesting is a smaller harm than losing the words. They become ordinary
    # top-level comments, which is what they were before this revision existed.
    op.drop_index("ix_comments_parent_id", table_name="comments")
    with op.batch_alter_table("comments") as batch:
        batch.drop_constraint("fk_comments_parent_id", type_="foreignkey")
        batch.drop_column("parent_id")
