"""
Collaboration models - comments, reviews, and approval gates.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.user import User
    from src.kernel.models.artifact import Artifact


class ReviewStatus(str, Enum):
    """Status of a review request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class CommentThread(Base, TimestampMixin):
    """A comment thread attached to an artifact."""
    
    __tablename__ = "comment_threads"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Thread state
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Relationships
    artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        back_populates="comment_threads",
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    
    def __repr__(self) -> str:
        return f"<CommentThread {self.id} artifact={self.artifact_id}>"


class Comment(Base, TimestampMixin):
    """A single comment in a thread."""
    
    __tablename__ = "comments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("comment_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Edit tracking
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    thread: Mapped["CommentThread"] = relationship(
        "CommentThread",
        back_populates="comments",
    )
    author: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
    )
    
    def __repr__(self) -> str:
        return f"<Comment {self.id} by {self.author_id}>"


class ReviewRequest(Base, TimestampMixin):
    """Request for advisor review of a project or artifact."""
    
    __tablename__ = "review_requests"
    
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
    submission_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("submission_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    status: Mapped[ReviewStatus] = mapped_column(
        String(50),
        default=ReviewStatus.PENDING,
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    response_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    strengths: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    weaknesses: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    required_changes: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    optional_suggestions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<ReviewRequest {self.id} status={self.status.value}>"


class ApprovalGate(Base, TimestampMixin):
    """Gate that must be passed before project progression."""
    
    __tablename__ = "approval_gates"
    
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
    
    gate_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    gate_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Gate state
    passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    passed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    passed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=True,
    )
    
    # Requirements
    requirements: Mapped[Optional[dict]] = mapped_column(
        type_=Text,  # Store as JSON string
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return f"<ApprovalGate {self.gate_name} passed={self.passed}>"
