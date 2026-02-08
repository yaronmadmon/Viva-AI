"""
Artifact schemas.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.kernel.models.artifact import (
    ArtifactType,
    LinkType,
    ClaimType,
    EvidenceType,
    ContributionCategory,
)


class ArtifactCreate(BaseModel):
    """Artifact creation request."""
    
    artifact_type: ArtifactType
    title: Optional[str] = Field(None, max_length=500)
    content: str = ""
    parent_id: Optional[uuid.UUID] = None
    position: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    # Type-specific fields
    claim_type: Optional[ClaimType] = None
    evidence_type: Optional[EvidenceType] = None
    citation_data: Optional[Dict[str, Any]] = None


class ArtifactUpdate(BaseModel):
    """Artifact update request."""
    
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    position: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ArtifactResponse(BaseModel):
    """Artifact response."""
    
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_type: str
    title: Optional[str]
    content: str
    content_hash: str
    version: int
    parent_id: Optional[uuid.UUID]
    position: int
    contribution_category: str
    ai_modification_ratio: float
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    # Counts
    children_count: int = 0
    outgoing_links_count: int = 0
    incoming_links_count: int = 0
    comment_count: int = 0
    
    class Config:
        from_attributes = True


class ArtifactDetailResponse(ArtifactResponse):
    """Detailed artifact response with related data."""
    
    children: List["ArtifactResponse"] = []
    outgoing_links: List["ArtifactLinkResponse"] = []
    incoming_links: List["ArtifactLinkResponse"] = []


class ArtifactLinkCreate(BaseModel):
    """Artifact link creation request."""
    
    target_artifact_id: uuid.UUID
    link_type: LinkType
    strength: float = Field(1.0, ge=0.0, le=1.0)
    annotation: Optional[str] = None


class ArtifactLinkResponse(BaseModel):
    """Artifact link response."""
    
    id: uuid.UUID
    source_artifact_id: uuid.UUID
    target_artifact_id: uuid.UUID
    link_type: str
    strength: float
    annotation: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    
    # Linked artifact info
    target_title: Optional[str] = None
    target_type: Optional[str] = None
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class ArtifactVersionResponse(BaseModel):
    """Artifact version response."""
    
    id: uuid.UUID
    artifact_id: uuid.UUID
    version_number: int
    title: Optional[str]
    content: str
    content_hash: str
    contribution_category: str
    created_by: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ArtifactTreeNode(BaseModel):
    """Node in the artifact tree."""
    
    id: uuid.UUID
    artifact_type: str
    title: Optional[str]
    position: int
    version: int
    children: List["ArtifactTreeNode"] = []


class ArtifactTreeResponse(BaseModel):
    """Full artifact tree for a project."""
    
    project_id: uuid.UUID
    root_artifacts: List[ArtifactTreeNode]
    total_count: int


class ArtifactMoveRequest(BaseModel):
    """Request to move an artifact."""

    new_parent_id: Optional[uuid.UUID] = None
    new_position: int = 0


class ArtifactStateTransition(BaseModel):
    """Request to transition artifact state (for artifacts not in a unit)."""

    to_state: str


# Update forward references
ArtifactDetailResponse.model_rebuild()
ArtifactTreeNode.model_rebuild()
