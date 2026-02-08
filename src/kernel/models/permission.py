"""
Permission models for RBAC.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.kernel.models.base import Base, generate_uuid


class PermissionLevel(str, Enum):
    """Permission levels for access control."""
    NONE = "none"
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(str, Enum):
    """Types of resources that can have permissions."""
    PROJECT = "project"
    ARTIFACT = "artifact"
    COMMENT = "comment"


class Permission(Base):
    """
    Permission record for resource access.
    
    Used for fine-grained access control beyond project sharing.
    """
    
    __tablename__ = "permissions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    
    # Subject (who has the permission)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Resource (what the permission is for)
    resource_type: Mapped[ResourceType] = mapped_column(
        String(50),
        nullable=False,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        nullable=False,
    )
    
    # Permission level
    level: Mapped[PermissionLevel] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # Grant metadata
    granted_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Expiration (optional)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Revocation
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    __table_args__ = (
        Index("ix_permissions_user_resource", "user_id", "resource_type", "resource_id"),
        Index("ix_permissions_resource", "resource_type", "resource_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Permission user={self.user_id} {self.resource_type.value}:{self.resource_id} level={self.level.value}>"
    
    @property
    def is_valid(self) -> bool:
        """Check if permission is currently valid."""
        if self.revoked:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
