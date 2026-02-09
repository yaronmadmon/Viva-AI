"""
Project schemas.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.kernel.models.project import DisciplineType, ProjectStatus, PermissionLevel


class IntellectualPositioning(BaseModel):
    """Intellectual positioning metadata — forces the student to declare
    their scholarly stance before generation begins."""
    
    aligned_school: Optional[str] = Field(
        None,
        description="Which school of thought, theoretical tradition, or paradigm is this work aligned with?",
        max_length=1000,
    )
    rejected_positions: Optional[str] = Field(
        None,
        description="Which positions, assumptions, or interpretations does this dissertation reject or modify, and why?",
        max_length=2000,
    )
    expected_critics: Optional[str] = Field(
        None,
        description="Who would disagree with this framing, and on what grounds?",
        max_length=1000,
    )


class ProjectCreate(BaseModel):
    """Project creation request."""
    
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    discipline_type: DisciplineType = DisciplineType.MIXED
    positioning: Optional[IntellectualPositioning] = None


class ProjectUpdate(BaseModel):
    """Project update request."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    discipline_type: Optional[DisciplineType] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    """Project response."""
    
    id: uuid.UUID
    title: str
    description: Optional[str]
    discipline_type: str
    status: str
    owner_id: uuid.UUID
    owner_name: Optional[str] = None
    integrity_score: float
    export_blocked: bool
    artifact_count: int = 0
    generation_pending: bool = True  # True until AI has populated real content
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Project list item response."""
    
    id: uuid.UUID
    title: str
    description: Optional[str]
    discipline_type: str
    status: str
    owner_id: uuid.UUID
    owner_name: Optional[str] = None
    integrity_score: float
    is_owner: bool = False
    permission_level: str = "view"
    artifact_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectShareRequest(BaseModel):
    """Project share request."""
    
    email: str  # Email of user to share with
    permission_level: PermissionLevel = PermissionLevel.VIEW
    message: Optional[str] = None  # Optional invitation message


class CollaboratorResponse(BaseModel):
    """Collaborator info response."""
    
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    permission_level: str
    is_owner: bool
    accepted: bool = True


class ProjectStatsResponse(BaseModel):
    """Project statistics response."""
    
    artifact_count: int
    claim_count: int
    evidence_count: int
    source_count: int
    word_count: int
    link_count: int
    comment_count: int
    integrity_score: float
    ai_usage_count: int
    last_activity: Optional[datetime]


class DocumentChunk(BaseModel):
    """Single artifact as a chunk in the document view."""
    id: uuid.UUID
    artifact_type: str
    title: Optional[str]
    content: str


class ProjectDocumentResponse(BaseModel):
    """Ordered list of artifacts for document view (tree order)."""
    project_id: uuid.UUID
    artifacts: List[DocumentChunk]
