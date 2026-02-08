"""Submission unit schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubmissionUnitCreate(BaseModel):
    """Create a submission unit."""

    title: str = Field(..., max_length=500)
    artifact_ids: Optional[List[uuid.UUID]] = None


class SubmissionUnitUpdate(BaseModel):
    """Update a submission unit (title, artifact_ids only)."""

    title: Optional[str] = Field(None, max_length=500)
    artifact_ids: Optional[List[uuid.UUID]] = None


class SubmissionUnitStateTransition(BaseModel):
    """Request to transition unit state."""

    to_state: str


class SubmissionUnitResponse(BaseModel):
    """Submission unit response."""

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    artifact_ids: Optional[List[str]] = None
    state: str
    state_changed_at: Optional[datetime] = None
    state_changed_by: Optional[uuid.UUID] = None
    current_review_request_id: Optional[uuid.UUID] = None
    last_approved_at: Optional[datetime] = None
    approval_version: Optional[int] = None
    created_at: datetime
    updated_at: datetime
