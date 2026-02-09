"""
Mastery models - user progress and checkpoint attempts.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.user import User
    from src.kernel.models.project import ResearchProject


class UserMasteryProgress(Base, TimestampMixin):
    """
    Per-user, per-project mastery progress.
    Tracks tier, AI disclosure level, word count, and advisor overrides.
    """

    __tablename__ = "user_mastery_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    current_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_disclosure_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_words_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tier_1_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    tier_2_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    tier_3_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    has_advisor_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    # Teaching avatar contract
    teacher_contract_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("user_id", "project_id", name="uq_user_mastery_progress_user_project"),)


class CheckpointAttempt(Base):
    """Record of a single checkpoint attempt."""

    __tablename__ = "checkpoint_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    checkpoint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_checkpoint_attempts_user_project_type", "user_id", "project_id", "checkpoint_type"),
    )
