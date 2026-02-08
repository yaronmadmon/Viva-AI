"""
Event type definitions using Pydantic for validation.

These are the payload schemas for events logged to the audit trail.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event payload structure."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


# User Events

class UserEvent(BaseEvent):
    """User-related event payloads."""
    
    email: Optional[str] = None
    role: Optional[str] = None
    previous_role: Optional[str] = None


class UserRegisteredEvent(UserEvent):
    """User registration event."""
    
    verification_sent: bool = False


class UserLoggedInEvent(UserEvent):
    """User login event."""
    
    method: str = "password"  # password, sso, etc.


# Project Events

class ProjectEvent(BaseEvent):
    """Project-related event payloads."""
    
    title: Optional[str] = None
    status: Optional[str] = None
    previous_status: Optional[str] = None


class ProjectCreatedEvent(ProjectEvent):
    """Project creation event."""
    
    discipline_type: str = "mixed"


class ProjectSharedEvent(ProjectEvent):
    """Project sharing event."""
    
    shared_with_user_id: uuid.UUID
    permission_level: str
    invited_by: uuid.UUID


class ProjectExportedEvent(ProjectEvent):
    """Project export event."""
    
    export_format: str
    integrity_score: float
    blocked: bool = False


# Artifact Events

class ArtifactEvent(BaseEvent):
    """Artifact-related event payloads."""
    
    project_id: Optional[uuid.UUID] = None
    artifact_type: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None


class ArtifactCreatedEvent(ArtifactEvent):
    """Artifact creation event."""
    
    title: Optional[str] = None
    content_hash: str
    contribution_category: str = "primarily_human"


class ArtifactUpdatedEvent(ArtifactEvent):
    """Artifact update event."""
    
    previous_content_hash: str
    new_content_hash: str
    version_number: int
    change_type: str = "edit"  # edit, ai_suggestion, etc.
    modification_ratio: float = 1.0


class ArtifactLinkedEvent(ArtifactEvent):
    """Artifact linking event."""
    
    source_artifact_id: uuid.UUID
    target_artifact_id: uuid.UUID
    link_type: str
    strength: float = 1.0


class ArtifactDeletedEvent(ArtifactEvent):
    """Artifact deletion event."""
    
    soft_delete: bool = True


# Collaboration Events

class CollaborationEvent(BaseEvent):
    """Collaboration-related event payloads."""
    
    project_id: Optional[uuid.UUID] = None
    artifact_id: Optional[uuid.UUID] = None


class CommentAddedEvent(CollaborationEvent):
    """Comment added event."""
    
    thread_id: uuid.UUID
    content_preview: str  # First 100 chars


class ReviewRequestedEvent(CollaborationEvent):
    """Review request event."""
    
    reviewer_id: uuid.UUID
    message: Optional[str] = None


class ReviewRespondedEvent(CollaborationEvent):
    """Review response event."""
    
    review_id: uuid.UUID
    status: str
    response_message: Optional[str] = None


# AI Events

class AIEvent(BaseEvent):
    """AI interaction event payloads."""
    
    suggestion_type: Optional[str] = None
    artifact_id: Optional[uuid.UUID] = None


class AISuggestionGeneratedEvent(AIEvent):
    """AI suggestion generated event."""
    
    suggestion_id: uuid.UUID
    content_hash: str
    confidence_score: float
    word_count: int
    watermarked: bool = True


class AISuggestionAcceptedEvent(AIEvent):
    """AI suggestion accepted event."""
    
    suggestion_id: uuid.UUID
    modification_ratio: float
    contribution_category: str


class AISuggestionRejectedEvent(AIEvent):
    """AI suggestion rejected event."""
    
    suggestion_id: uuid.UUID
    reason: Optional[str] = None


# Mastery Events

class MasteryEvent(BaseEvent):
    """Mastery checkpoint event payloads."""
    
    tier: Optional[int] = None
    checkpoint_type: Optional[str] = None


class CheckpointCompletedEvent(MasteryEvent):
    """Checkpoint completion event."""
    
    checkpoint_id: uuid.UUID
    passed: bool
    score: float
    attempts: int
    time_spent_seconds: int


class TierUpgradedEvent(MasteryEvent):
    """Tier upgrade event."""
    
    previous_tier: int
    new_tier: int
    ai_level_unlocked: int


# Validation Events

class ValidationEvent(BaseEvent):
    """Validation-related event payloads."""
    
    source_id: Optional[uuid.UUID] = None
    artifact_id: Optional[uuid.UUID] = None


class CitationVerifiedEvent(ValidationEvent):
    """Citation verification event."""
    
    verification_layer: int  # 1-5
    verification_status: str
    doi: Optional[str] = None
    api_response: Optional[Dict[str, Any]] = None


class RedFlagDetectedEvent(ValidationEvent):
    """Red flag detection event."""
    
    flag_type: str
    description: str
    blocks_export: bool = True


# Export Events

class ExportEvent(BaseEvent):
    """Export-related event payloads."""
    
    project_id: uuid.UUID
    export_format: str


class ExportCompletedEvent(ExportEvent):
    """Export completion event."""
    
    file_size_bytes: int
    integrity_score: float
    warnings: List[str] = Field(default_factory=list)


class ExportBlockedEvent(ExportEvent):
    """Export blocked event."""
    
    reason: str
    blocking_issues: List[str] = Field(default_factory=list)
    integrity_score: float
