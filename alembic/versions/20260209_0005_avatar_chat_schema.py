"""Avatar chat schema - add teacher_contract_accepted column and avatar_messages table

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing teacher_contract_accepted column to user_mastery_progress
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [c["name"] for c in inspector.get_columns("user_mastery_progress")]
    if "teacher_contract_accepted" not in columns:
        op.add_column(
            "user_mastery_progress",
            sa.Column(
                "teacher_contract_accepted",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )

    # Create avatar_messages table if it doesn't exist
    tables = inspector.get_table_names()
    if "avatar_messages" not in tables:
        op.create_table(
            "avatar_messages",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "project_id",
                sa.Uuid(),
                sa.ForeignKey("research_projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("teaching_mode", sa.String(20), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_avatar_messages_project_user_created",
            "avatar_messages",
            ["project_id", "user_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_avatar_messages_project_user_created",
        table_name="avatar_messages",
    )
    op.drop_table("avatar_messages")
    op.drop_column("user_mastery_progress", "teacher_contract_accepted")
