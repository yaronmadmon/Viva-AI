"""
User model for identity management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.project import ResearchProject, ProjectShare
    from src.kernel.models.collaboration import Comment


class UserRole(str, Enum):
    """User roles in the system."""
    STUDENT = "student"
    ADVISOR = "advisor"
    EXAMINER = "examiner"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.STUDENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Mastery tracking
    mastery_tier: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    ai_disclosure_level: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    total_words_written: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    
    # Relationships
    owned_projects: Mapped[List["ResearchProject"]] = relationship(
        "ResearchProject",
        back_populates="owner",
        foreign_keys="ResearchProject.owner_id",
    )
    shared_projects: Mapped[List["ProjectShare"]] = relationship(
        "ProjectShare",
        back_populates="user",
        foreign_keys="ProjectShare.user_id",
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="author",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"


class RefreshToken(Base):
    """Refresh token for JWT authentication."""
    
    __tablename__ = "refresh_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
