"""
Pydantic schemas for validation API.
"""

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ValidationRunResponse(BaseModel):
    """Response from batch validation run."""

    project_id: uuid.UUID
    total_sources: int
    results: Dict[str, Any]  # str(artifact_id) -> FullValidationResult as dict
    created_verification_request_ids: List[uuid.UUID] = []
    overall_blocks_export: bool = False
    summary: str = ""
