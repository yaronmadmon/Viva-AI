"""Mastery and verification schema - Phase 1B

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sources table (artifact extension for citations)
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("citation_data", sa.JSON(), nullable=False),
        sa.Column("doi", sa.String(255), nullable=True, index=True),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("access_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(50), nullable=False, server_default="unverified"),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Claims table (artifact extension)
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("claim_type", sa.String(50), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Evidence table (artifact extension)
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("strength_rating", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source_refs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Provenance records (depends on sources)
    op.create_table(
        "provenance_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("retrieval_method", sa.String(100), nullable=False),
        sa.Column("verification_hash", sa.String(64), nullable=False),
        sa.Column("verified_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # User mastery progress (per user, per project)
    op.create_table(
        "user_mastery_progress",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("current_tier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_disclosure_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_words_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tier_1_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tier_2_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tier_3_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_advisor_override", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("override_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_user_mastery_progress_user_project", "user_mastery_progress", ["user_id", "project_id"])

    # Checkpoint attempts
    op.create_table(
        "checkpoint_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("checkpoint_type", sa.String(50), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_checkpoint_attempts_user_project_type",
        "checkpoint_attempts",
        ["user_id", "project_id", "checkpoint_type"],
    )

    # Content verification requests
    op.create_table(
        "content_verification_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("claim_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("check_type", sa.String(50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("content_verification_requests")
    op.drop_index("ix_checkpoint_attempts_user_project_type", table_name="checkpoint_attempts")
    op.drop_table("checkpoint_attempts")
    op.drop_constraint("uq_user_mastery_progress_user_project", "user_mastery_progress", type_="unique")
    op.drop_table("user_mastery_progress")
    op.drop_table("provenance_records")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("sources")
