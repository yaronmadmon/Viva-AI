"""Submission units and artifact state - Phase A

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Submission units table
    op.create_table(
        "submission_units",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("artifact_ids", sa.JSON(), nullable=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state_changed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_review_request_id", sa.Uuid(), nullable=True),
        sa.Column("last_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_submission_units_project_state", "submission_units", ["project_id", "state"])

    # Add columns to artifacts
    op.add_column("artifacts", sa.Column("submission_unit_id", sa.Uuid(), nullable=True))
    op.add_column("artifacts", sa.Column("internal_state", sa.String(50), nullable=False, server_default="draft"))
    op.create_foreign_key(
        "fk_artifacts_submission_unit_id",
        "artifacts",
        "submission_units",
        ["submission_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_artifacts_submission_unit_id", "artifacts", ["submission_unit_id"])


def downgrade() -> None:
    op.drop_index("ix_artifacts_submission_unit_id", table_name="artifacts")
    op.drop_constraint("fk_artifacts_submission_unit_id", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "internal_state")
    op.drop_column("artifacts", "submission_unit_id")
    op.drop_index("ix_submission_units_project_state", table_name="submission_units")
    op.drop_table("submission_units")
