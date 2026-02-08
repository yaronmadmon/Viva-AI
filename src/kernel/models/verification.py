"""
Content verification models - manual verification requests and responses.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.kernel.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.artifact import Source
    from src.kernel.models.user import User


class ContentVerificationRequest(Base, TimestampMixin):
    """
    A request for manual content verification (e.g. author/date match, supports claim).
    Resolution fields are filled when the user responds.
    """

    __tablename__ = "content_verification_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=generate_uuid,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resolution (filled when user responds)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
