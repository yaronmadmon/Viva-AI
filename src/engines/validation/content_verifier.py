"""
Layer 3: Content Spot Check - Manual verification support.

Provides UI support for users to confirm that sources actually
support the claims they're linked to.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel

from src.engines.validation.format_validator import ValidationResult, ValidationStatus


class VerificationCheckType(str, Enum):
    """Types of content verification checks."""
    SUPPORTS_CLAIM = "supports_claim"
    AUTHOR_MATCHES = "author_matches"
    DATE_MATCHES = "date_matches"
    QUOTE_ACCURATE = "quote_accurate"
    PAGE_NUMBER_VALID = "page_number_valid"


class ContentVerificationRequest(BaseModel):
    """Request for manual content verification."""
    
    source_id: uuid.UUID
    claim_id: uuid.UUID
    check_type: VerificationCheckType
    prompt: str  # Question to ask user
    context: Optional[str] = None  # Relevant text to show user


class ContentVerificationResponse(BaseModel):
    """User's response to verification request."""
    
    request_id: uuid.UUID
    user_id: uuid.UUID
    verified: bool
    notes: Optional[str] = None
    verified_at: datetime


class ContentVerifier:
    """
    Layer 3: Content spot check verification.
    
    Creates verification requests for users to manually confirm
    that sources support the claims they're linked to.
    """
    
    @classmethod
    def create_supports_claim_check(
        cls,
        source_id: uuid.UUID,
        claim_id: uuid.UUID,
        claim_text: str,
        source_title: str,
    ) -> ContentVerificationRequest:
        """Create a check for whether source supports claim."""
        return ContentVerificationRequest(
            source_id=source_id,
            claim_id=claim_id,
            check_type=VerificationCheckType.SUPPORTS_CLAIM,
            prompt=f"Does the source '{source_title}' support the claim: '{claim_text}'?",
            context=claim_text,
        )
    
    @classmethod
    def create_author_check(
        cls,
        source_id: uuid.UUID,
        claim_id: uuid.UUID,
        cited_author: str,
        api_author: Optional[str],
    ) -> ContentVerificationRequest:
        """Create a check for author name mismatch."""
        return ContentVerificationRequest(
            source_id=source_id,
            claim_id=claim_id,
            check_type=VerificationCheckType.AUTHOR_MATCHES,
            prompt=f"You cited '{cited_author}' but API returned '{api_author}'. Is this the same author?",
            context=f"Cited: {cited_author}\nAPI: {api_author}",
        )
    
    @classmethod
    def create_date_check(
        cls,
        source_id: uuid.UUID,
        claim_id: uuid.UUID,
        cited_year: int,
        api_year: Optional[int],
    ) -> ContentVerificationRequest:
        """Create a check for publication date mismatch."""
        return ContentVerificationRequest(
            source_id=source_id,
            claim_id=claim_id,
            check_type=VerificationCheckType.DATE_MATCHES,
            prompt=f"You cited year {cited_year} but API returned {api_year}. Which is correct?",
            context=f"Cited: {cited_year}\nAPI: {api_year}",
        )
    
    @classmethod
    def evaluate_verification(
        cls,
        response: ContentVerificationResponse,
    ) -> ValidationResult:
        """Evaluate a verification response."""
        if response.verified:
            return ValidationResult(
                status=ValidationStatus.VALID,
                layer=3,
                message="Content verified by user",
                details={
                    "verified_by": str(response.user_id),
                    "verified_at": response.verified_at.isoformat(),
                    "notes": response.notes,
                },
            )
        else:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                layer=3,
                message="User indicated content does not match",
                details={
                    "verified_by": str(response.user_id),
                    "notes": response.notes,
                },
            )
