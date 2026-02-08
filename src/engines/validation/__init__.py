"""
Validation Engine - 5-layer citation verification.

Layers:
1. Format Validation (local) - DOI/ISBN format checking
2. Existence Check (API) - Crossref, OpenLibrary, arXiv verification
3. Content Spot Check (manual) - User confirms source supports claim
4. Cross-Project Warning (automated) - Conflicting interpretations flagged
5. Red Flags (blocking) - Non-existent DOI, date/author mismatch
"""

from src.engines.validation.format_validator import FormatValidator, ValidationResult
from src.engines.validation.existence_checker import ExistenceChecker
from src.engines.validation.content_verifier import ContentVerifier
from src.engines.validation.cross_project_checker import CrossProjectChecker
from src.engines.validation.red_flag_detector import RedFlagDetector
from src.engines.validation.validation_service import ValidationService

__all__ = [
    "FormatValidator",
    "ValidationResult",
    "ExistenceChecker",
    "ContentVerifier",
    "CrossProjectChecker",
    "RedFlagDetector",
    "ValidationService",
]
