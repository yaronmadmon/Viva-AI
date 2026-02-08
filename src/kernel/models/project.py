"""
Research project models.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.user import User
    from src.kernel.models.artifact import Artifact
    from src.kernel.models.submission_unit import SubmissionUnit


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class DisciplineType(str, Enum):
    """Academic discipline types."""
    STEM = "stem"
    HUMANITIES = "humanities"
    SOCIAL_SCIENCES = "social_sciences"
    LEGAL = "legal"
    MIXED = "mixed"


class PermissionLevel(str, Enum):
    """Permission levels for project sharing."""
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"


class ResearchProject(Base, TimestampMixin, SoftDeleteMixin):
    """Top-level research project container."""
    
    __tablename__ = "research_projects"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    discipline_type: Mapped[DisciplineType] = mapped_column(
        String(50),
        default=DisciplineType.MIXED,
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        String(50),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )
    
    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    
    # Integrity tracking
    integrity_score: Mapped[float] = mapped_column(
        default=100.0,
        nullable=False,
    )
    export_blocked: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_projects",
        foreign_keys=[owner_id],
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    shares: Mapped[List["ProjectShare"]] = relationship(
        "ProjectShare",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    submission_units: Mapped[List["SubmissionUnit"]] = relationship(
        "SubmissionUnit",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ResearchProject {self.title[:50]}>"


class ProjectShare(Base, TimestampMixin):
    """Project sharing/collaboration record."""
    
    __tablename__ = "project_shares"
    
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    permission_level: Mapped[PermissionLevel] = mapped_column(
        String(50),
        default=PermissionLevel.VIEW,
        nullable=False,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    project: Mapped["ResearchProject"] = relationship(
        "ResearchProject",
        back_populates="shares",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="shared_projects",
        foreign_keys=[user_id],
    )
    
    def __repr__(self) -> str:
        return f"<ProjectShare project={self.project_id} user={self.user_id}>"
