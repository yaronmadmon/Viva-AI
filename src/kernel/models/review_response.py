"""
ReviewResponse model - student's response to advisor feedback.

Required for revisions_required -> ready_for_review when >=80% of
required_changes addressed.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Index, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.kernel.models.base import Base, generate_uuid


class ReviewResponse(Base):
    """Student response to advisor review feedback."""

    __tablename__ = "review_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    review_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("submission_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    changes_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    addressed_items: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )
    disputed_items: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )
    new_version_ids: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
    )
    changelog: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_review_responses_review_request", "review_request_id"),
        Index("ix_review_responses_submission_unit", "submission_unit_id"),
    )
