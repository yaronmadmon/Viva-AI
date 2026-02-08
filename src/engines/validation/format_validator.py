"""
Layer 1: Format Validation - Local validation of citation formats.
"""

import re
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class ValidationStatus(str, Enum):
    """Validation status."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class ValidationResult(BaseModel):
    """Result of a validation check."""
    
    status: ValidationStatus
    layer: int
    message: str
    field: Optional[str] = None
    details: Optional[dict] = None


class FormatValidator:
    """
    Layer 1: Format validation for citations.
    
    Validates DOIs, ISBNs, and required citation fields.
    Runs locally without external API calls.
    """
    
    # DOI regex pattern (https://www.doi.org/doi_handbook/2_Numbering.html)
    DOI_PATTERN = re.compile(r'^10\.\d{4,}(\.\d+)*/[^\s]+$')
    
    # ISBN-10 and ISBN-13 patterns
    ISBN10_PATTERN = re.compile(r'^(?:\d[- ]?){9}[\dXx]$')
    ISBN13_PATTERN = re.compile(r'^(?:978|979)[- ]?(?:\d[- ]?){9}\d$')
    
    # arXiv pattern
    ARXIV_PATTERN = re.compile(r'^(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})v?\d*$')
    
    # Required fields for different source types
    REQUIRED_FIELDS = {
        "journal": ["title", "authors", "journal", "year"],
        "book": ["title", "authors", "year"],
        "conference": ["title", "authors", "conference", "year"],
        "webpage": ["title", "url", "access_date"],
        "thesis": ["title", "author", "institution", "year"],
    }
    
    @classmethod
    def validate_doi(cls, doi: str) -> ValidationResult:
        """Validate DOI format."""
        if not doi:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                layer=1,
                message="DOI is empty",
                field="doi",
            )
        
        # Clean DOI
        doi = doi.strip()
        
        # Remove common prefixes
        for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]
        
        if cls.DOI_PATTERN.match(doi):
            return ValidationResult(
                status=ValidationStatus.VALID,
                layer=1,
                message="DOI format is valid",
                field="doi",
                details={"normalized_doi": doi},
            )
        
        return ValidationResult(
            status=ValidationStatus.INVALID,
            layer=1,
            message="Invalid DOI format",
            field="doi",
            details={"input": doi},
        )
    
    @classmethod
    def validate_isbn(cls, isbn: str) -> ValidationResult:
        """Validate ISBN format and checksum."""
        if not isbn:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                layer=1,
                message="ISBN is empty",
                field="isbn",
            )
        
        # Clean ISBN
        isbn_clean = re.sub(r'[- ]', '', isbn.strip())
        
        # Check format
        if len(isbn_clean) == 10:
            if not cls.ISBN10_PATTERN.match(isbn):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=1,
                    message="Invalid ISBN-10 format",
                    field="isbn",
                )
            
            # Validate checksum
            if cls._validate_isbn10_checksum(isbn_clean):
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    layer=1,
                    message="ISBN-10 is valid",
                    field="isbn",
                    details={"normalized_isbn": isbn_clean},
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=1,
                    message="ISBN-10 checksum is invalid",
                    field="isbn",
                )
        
        elif len(isbn_clean) == 13:
            if not isbn_clean.isdigit():
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=1,
                    message="Invalid ISBN-13 format",
                    field="isbn",
                )
            
            # Validate checksum
            if cls._validate_isbn13_checksum(isbn_clean):
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    layer=1,
                    message="ISBN-13 is valid",
                    field="isbn",
                    details={"normalized_isbn": isbn_clean},
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=1,
                    message="ISBN-13 checksum is invalid",
                    field="isbn",
                )
        
        return ValidationResult(
            status=ValidationStatus.INVALID,
            layer=1,
            message="ISBN must be 10 or 13 characters",
            field="isbn",
        )
    
    @classmethod
    def validate_arxiv(cls, arxiv_id: str) -> ValidationResult:
        """Validate arXiv ID format."""
        if not arxiv_id:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                layer=1,
                message="arXiv ID is empty",
                field="arxiv",
            )
        
        arxiv_id = arxiv_id.strip()
        
        # Remove common prefixes
        for prefix in ["arXiv:", "arxiv:"]:
            if arxiv_id.startswith(prefix):
                arxiv_id = arxiv_id[len(prefix):]
        
        if cls.ARXIV_PATTERN.match(arxiv_id):
            return ValidationResult(
                status=ValidationStatus.VALID,
                layer=1,
                message="arXiv ID format is valid",
                field="arxiv",
                details={"normalized_id": arxiv_id},
            )
        
        return ValidationResult(
            status=ValidationStatus.INVALID,
            layer=1,
            message="Invalid arXiv ID format",
            field="arxiv",
        )
    
    @classmethod
    def validate_required_fields(
        cls,
        source_type: str,
        citation_data: dict,
    ) -> List[ValidationResult]:
        """Check that required fields are present for source type."""
        results = []
        
        required = cls.REQUIRED_FIELDS.get(source_type, [])
        
        for field in required:
            if field not in citation_data or not citation_data[field]:
                results.append(ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=1,
                    message=f"Required field '{field}' is missing",
                    field=field,
                ))
            else:
                results.append(ValidationResult(
                    status=ValidationStatus.VALID,
                    layer=1,
                    message=f"Field '{field}' is present",
                    field=field,
                ))
        
        return results
    
    @classmethod
    def validate_year(cls, year: int) -> ValidationResult:
        """Validate publication year is reasonable."""
        from datetime import datetime
        
        current_year = datetime.now().year
        
        if year < 1450:  # Before printing press
            return ValidationResult(
                status=ValidationStatus.INVALID,
                layer=1,
                message="Year is before the printing press era",
                field="year",
            )
        
        if year > current_year + 1:  # Allow next year for forthcoming
            return ValidationResult(
                status=ValidationStatus.WARNING,
                layer=1,
                message="Year is in the future",
                field="year",
            )
        
        return ValidationResult(
            status=ValidationStatus.VALID,
            layer=1,
            message="Year is valid",
            field="year",
        )
    
    @staticmethod
    def _validate_isbn10_checksum(isbn: str) -> bool:
        """Validate ISBN-10 checksum."""
        total = 0
        for i, char in enumerate(isbn):
            if char in 'Xx':
                value = 10
            else:
                value = int(char)
            total += value * (10 - i)
        return total % 11 == 0
    
    @staticmethod
    def _validate_isbn13_checksum(isbn: str) -> bool:
        """Validate ISBN-13 checksum."""
        total = 0
        for i, char in enumerate(isbn):
            if i % 2 == 0:
                total += int(char)
            else:
                total += int(char) * 3
        return total % 10 == 0
