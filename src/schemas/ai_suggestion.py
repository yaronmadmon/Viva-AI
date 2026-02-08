"""
Pydantic schemas for AI suggestion API.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AISuggestionGenerateRequest(BaseModel):
    """Request to generate an AI suggestion for an artifact."""

    artifact_id: uuid.UUID
    suggestion_type: str  # outline, paragraph_draft, source_summary, etc.
    additional_instructions: Optional[str] = None


class AISuggestionGenerateResponse(BaseModel):
    """Response from AI suggestion generation."""

    suggestion_id: uuid.UUID
    suggestion_type: str
    content: str
    confidence: float
    watermark_hash: str
    word_count: int
    truncated: bool
    requires_checkbox: bool
    min_modification_required: Optional[float] = None
    generated_at: datetime
    model_used: str = "stub"


class AISuggestionAcceptRequest(BaseModel):
    """Request to accept an AI suggestion (optionally with user edits)."""

    suggestion_id: uuid.UUID
    artifact_id: uuid.UUID
    suggestion_type: str
    modified_content: Optional[str] = None
    modification_ratio: Optional[float] = None


class AISuggestionRejectRequest(BaseModel):
    """Request to reject an AI suggestion."""

    suggestion_id: uuid.UUID
    artifact_id: uuid.UUID
    suggestion_type: str
