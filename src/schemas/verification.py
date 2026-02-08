"""
Pydantic schemas for content verification API.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContentVerificationRequestCreate(BaseModel):
    """Create a content verification request."""

    source_id: uuid.UUID
    claim_id: uuid.UUID
    check_type: str = Field(..., description="e.g. supports_claim, author_matches, date_matches")
    prompt: str
    context: Optional[str] = None


class VerifyResponseBody(BaseModel):
    """Body for responding to a verification request."""

    verified: bool
    notes: Optional[str] = None


class ContentVerificationRequestResponse(BaseModel):
    """Response model for a content verification request (persisted)."""

    id: uuid.UUID
    source_id: uuid.UUID
    claim_id: uuid.UUID
    check_type: str
    prompt: str
    context: Optional[str] = None
    resolved: bool = False
    verified: Optional[bool] = None
    notes: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
