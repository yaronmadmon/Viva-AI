"""
Base model with common fields and utilities.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    # Use generic Uuid type for cross-database compatibility
    type_annotation_map = {
        uuid.UUID: Uuid(),
    }


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID."""
    return uuid.uuid4()
