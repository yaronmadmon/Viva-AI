"""
Avatar conversation models – persistent message history for the teaching avatar.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.kernel.models.base import Base, generate_uuid


class AvatarMessage(Base):
    """
    Single message in an avatar teaching conversation.

    Stores the full conversation history per user+project so the avatar
    can sustain multi-turn Socratic exchanges and remember context.
    """

    __tablename__ = "avatar_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=generate_uuid,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # "user" | "assistant" | "system"

    content: Mapped[str] = mapped_column(Text, nullable=False)

    teaching_mode: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
    )  # PROBE | HINT | EXPLAIN | EXAMINER | REFLECTION

    token_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )  # approximate token count for context window management

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_avatar_messages_project_user_created",
            "project_id", "user_id", "created_at",
        ),
    )
