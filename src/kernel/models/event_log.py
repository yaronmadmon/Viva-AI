"""
Immutable event log for audit trail.

All state mutations are logged here BEFORE commit.
This implements the append-only audit requirement.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, String, Text, func, Index, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.kernel.models.base import Base, generate_uuid


class EventType(str, Enum):
    """All event types for the audit log."""
    
    # User events
    USER_REGISTERED = "user.registered"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    USER_UPDATED = "user.updated"
    USER_ROLE_CHANGED = "user.role_changed"
    
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    PROJECT_STATUS_CHANGED = "project.status_changed"
    PROJECT_SHARED = "project.shared"
    PROJECT_UNSHARED = "project.unshared"
    PROJECT_EXPORTED = "project.exported"
    
    # Artifact events
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"
    ARTIFACT_DELETED = "artifact.deleted"
    ARTIFACT_LINKED = "artifact.linked"
    ARTIFACT_UNLINKED = "artifact.unlinked"
    ARTIFACT_MOVED = "artifact.moved"
    
    # Collaboration events
    COMMENT_ADDED = "comment.added"
    COMMENT_EDITED = "comment.edited"
    COMMENT_DELETED = "comment.deleted"
    THREAD_RESOLVED = "thread.resolved"
    THREAD_REOPENED = "thread.reopened"
    REVIEW_REQUESTED = "review.requested"
    REVIEW_RESPONDED = "review.responded"
    
    # AI events
    AI_SUGGESTION_GENERATED = "ai.suggestion_generated"
    AI_SUGGESTION_ACCEPTED = "ai.suggestion_accepted"
    AI_SUGGESTION_REJECTED = "ai.suggestion_rejected"
    AI_SUGGESTION_MODIFIED = "ai.suggestion_modified"
    
    # Mastery events
    CHECKPOINT_STARTED = "mastery.checkpoint_started"
    CHECKPOINT_PASSED = "mastery.checkpoint_passed"
    CHECKPOINT_FAILED = "mastery.checkpoint_failed"
    TIER_UPGRADED = "mastery.tier_upgraded"
    AI_LEVEL_UNLOCKED = "mastery.ai_level_unlocked"
    
    # Validation events
    CITATION_VERIFIED = "validation.citation_verified"
    CITATION_FLAGGED = "validation.citation_flagged"
    RED_FLAG_DETECTED = "validation.red_flag_detected"
    
    # Export events
    EXPORT_REQUESTED = "export.requested"
    EXPORT_COMPLETED = "export.completed"
    EXPORT_BLOCKED = "export.blocked"
    INTEGRITY_REPORT_GENERATED = "export.integrity_report"
    
    # Admin events
    ADVISOR_OVERRIDE = "admin.advisor_override"
    BULK_OPERATION = "admin.bulk_operation"

    # Orchestration events (Phase A+)
    SUBMISSION_UNIT_STATE_CHANGED = "submission_unit.state_changed"
    ARTIFACT_STATE_CHANGED = "artifact.state_changed"


class EventLog(Base):
    """
    Immutable audit event log.
    
    This table is append-only - no updates or deletes allowed.
    All significant actions must be logged here before committing.
    """
    
    __tablename__ = "event_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    
    # Event identification
    event_type: Mapped[EventType] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    
    # Entity reference
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        nullable=False,
        index=True,
    )
    
    # Actor
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        nullable=True,  # System events may not have a user
        index=True,
    )
    
    # Event data
    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    
    # Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Timestamp (immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    __table_args__ = (
        Index("ix_event_logs_entity", "entity_type", "entity_id"),
        Index("ix_event_logs_user_time", "user_id", "created_at"),
        Index("ix_event_logs_type_time", "event_type", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<EventLog {self.event_type.value} {self.entity_type}:{self.entity_id}>"
