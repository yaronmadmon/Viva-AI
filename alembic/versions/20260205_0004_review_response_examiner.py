"""Review response and examiner - Phase B

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create review_requests if not exists (for alembic-only DBs)
    conn = op.get_bind()
    inspector = inspect(conn)
    if "review_requests" not in inspector.get_table_names():
        op.create_table(
            "review_requests",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("submission_unit_id", sa.Uuid(), sa.ForeignKey("submission_units.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=True),
            sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("response_message", sa.Text(), nullable=True),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("strengths", sa.Text(), nullable=True),
            sa.Column("weaknesses", sa.Text(), nullable=True),
            sa.Column("required_changes", sa.JSON(), nullable=True),
            sa.Column("optional_suggestions", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    else:
        # Add new columns to existing review_requests
        with op.batch_alter_table("review_requests", schema=None) as batch_op:
            batch_op.add_column(sa.Column("submission_unit_id", sa.Uuid(), nullable=True))
            batch_op.add_column(sa.Column("strengths", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("weaknesses", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("required_changes", sa.JSON(), nullable=True))
            batch_op.add_column(sa.Column("optional_suggestions", sa.Text(), nullable=True))
        op.create_foreign_key(
            "fk_review_requests_submission_unit",
            "review_requests",
            "submission_units",
            ["submission_unit_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_review_requests_submission_unit_id", "review_requests", ["submission_unit_id"])

    # Create approval_gates if not exists
    if "approval_gates" not in inspector.get_table_names():
        op.create_table(
            "approval_gates",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("project_id", sa.Uuid(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("gate_type", sa.String(100), nullable=False),
            sa.Column("gate_name", sa.String(255), nullable=False),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("passed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("passed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("requirements", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # Create review_responses
    op.create_table(
        "review_responses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("review_request_id", sa.Uuid(), sa.ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("submission_unit_id", sa.Uuid(), sa.ForeignKey("submission_units.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("changes_summary", sa.Text(), nullable=False),
        sa.Column("addressed_items", sa.JSON(), nullable=True),
        sa.Column("disputed_items", sa.JSON(), nullable=True),
        sa.Column("new_version_ids", sa.JSON(), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_responses_review_request", "review_responses", ["review_request_id"])
    op.create_index("ix_review_responses_submission_unit", "review_responses", ["submission_unit_id"])


def downgrade() -> None:
    op.drop_index("ix_review_responses_submission_unit", table_name="review_responses")
    op.drop_index("ix_review_responses_review_request", table_name="review_responses")
    op.drop_table("review_responses")
    # Note: not removing review_requests or approval_gates columns for safety