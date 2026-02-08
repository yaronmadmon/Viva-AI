"""
SubmissionUnit model - logical grouping of artifacts for review and export.

SubmissionUnit.state is authoritative for review, defense, and export.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Index, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.project import ResearchProject
    from src.kernel.models.artifact import Artifact
    from src.kernel.models.collaboration import ReviewRequest


class SubmissionUnitState(str, Enum):
    """State of a submission unit (and artifact when in a unit)."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    REVISIONS_REQUIRED = "revisions_required"
    APPROVED = "approved"
    LOCKED = "locked"
    ARCHIVED = "archived"


class SubmissionUnit(Base, TimestampMixin):
    """
    Logical grouping of artifacts (e.g. "Chapter 3") for review and export.

    SubmissionUnit.state is authoritative for review, defense, and export.
    One ReviewRequest per unit (or explicit batch).
    """

    __tablename__ = "submission_units"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Artifact IDs in this unit (JSON array)
    artifact_ids: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )

    # State (authoritative for review, defense, export)
    state: Mapped[SubmissionUnitState] = mapped_column(
        String(50),
        default=SubmissionUnitState.DRAFT,
        nullable=False,
    )
    state_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    state_changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Current review (one per unit) - FK added when ReviewRequest.submission_unit_id exists
    current_review_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        nullable=True,
    )

    last_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_version: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )

    # Relationships
    project: Mapped["ResearchProject"] = relationship(
        "ResearchProject",
        back_populates="submission_units",
    )

    __table_args__ = (
        Index("ix_submission_units_project_state", "project_id", "state"),
    )

    def __repr__(self) -> str:
        return f"<SubmissionUnit {self.title} {self.state.value}>"
