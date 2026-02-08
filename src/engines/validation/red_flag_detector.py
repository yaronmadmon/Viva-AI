"""
Layer 5: Red Flag Detection - Critical issues that block export.

Detects critical validation failures that should block export:
- Non-existent DOIs
- Significant date mismatches (>5 years)
- Author name completely different
- Suspected fabricated sources
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from src.engines.validation.format_validator import ValidationResult, ValidationStatus
from src.engines.validation.existence_checker import SourceMetadata


class RedFlagType(str, Enum):
    """Types of red flags."""
    NONEXISTENT_DOI = "nonexistent_doi"
    DATE_MISMATCH = "date_mismatch"
    AUTHOR_MISMATCH = "author_mismatch"
    SUSPICIOUS_CITATION = "suspicious_citation"
    DUPLICATE_CITATION = "duplicate_citation"
    SELF_CITATION_EXCESSIVE = "self_citation_excessive"


class RedFlag(BaseModel):
    """A detected red flag."""
    
    flag_type: RedFlagType
    source_id: uuid.UUID
    severity: str  # high, medium
    message: str
    details: Optional[dict] = None
    blocks_export: bool = True


class RedFlagDetector:
    """
    Layer 5: Red flag detection.
    
    Identifies critical issues that should block export.
    """
    
    # Date mismatch threshold (years)
    DATE_MISMATCH_THRESHOLD = 5
    
    # Self-citation threshold
    MAX_SELF_CITATION_RATIO = 0.3  # 30% max
    
    @classmethod
    def check_existence_failure(
        cls,
        source_id: uuid.UUID,
        doi: Optional[str],
        api_found: bool,
    ) -> Optional[RedFlag]:
        """Check if DOI doesn't exist."""
        if doi and not api_found:
            return RedFlag(
                flag_type=RedFlagType.NONEXISTENT_DOI,
                source_id=source_id,
                severity="high",
                message=f"DOI {doi} does not exist in Crossref",
                details={"doi": doi},
                blocks_export=True,
            )
        return None
    
    @classmethod
    def check_date_mismatch(
        cls,
        source_id: uuid.UUID,
        cited_year: Optional[int],
        api_year: Optional[int],
    ) -> Optional[RedFlag]:
        """Check for significant date mismatch."""
        if cited_year and api_year:
            diff = abs(cited_year - api_year)
            if diff > cls.DATE_MISMATCH_THRESHOLD:
                return RedFlag(
                    flag_type=RedFlagType.DATE_MISMATCH,
                    source_id=source_id,
                    severity="high",
                    message=f"Publication year mismatch: cited {cited_year}, actual {api_year}",
                    details={
                        "cited_year": cited_year,
                        "api_year": api_year,
                        "difference": diff,
                    },
                    blocks_export=True,
                )
        return None
    
    @classmethod
    def check_author_mismatch(
        cls,
        source_id: uuid.UUID,
        cited_authors: List[str],
        api_authors: Optional[List[str]],
    ) -> Optional[RedFlag]:
        """Check if author names are completely different."""
        if not cited_authors or not api_authors:
            return None
        
        # Simple check: see if any cited author appears in API authors
        cited_normalized = set(a.lower().split()[-1] for a in cited_authors)  # Last names
        api_normalized = set(a.lower().split()[-1] for a in api_authors)
        
        overlap = cited_normalized & api_normalized
        
        if not overlap:
            return RedFlag(
                flag_type=RedFlagType.AUTHOR_MISMATCH,
                source_id=source_id,
                severity="high",
                message="No author names match between citation and source",
                details={
                    "cited_authors": cited_authors,
                    "api_authors": api_authors,
                },
                blocks_export=True,
            )
        
        return None
    
    @classmethod
    def check_suspicious_patterns(
        cls,
        source_id: uuid.UUID,
        citation_data: dict,
    ) -> Optional[RedFlag]:
        """
        Check for suspicious citation patterns.
        
        STUB: In production, would check for:
        - Known fake journal names
        - Suspicious author name patterns
        - Impossible publication dates
        """
        # Check for obviously fake journal names
        journal = citation_data.get("journal", "").lower()
        suspicious_patterns = [
            "predatory",
            "pay to publish",
            "instant accept",
        ]
        
        for pattern in suspicious_patterns:
            if pattern in journal:
                return RedFlag(
                    flag_type=RedFlagType.SUSPICIOUS_CITATION,
                    source_id=source_id,
                    severity="medium",
                    message=f"Potentially suspicious journal: {citation_data.get('journal')}",
                    blocks_export=False,  # Warning only
                )
        
        return None
    
    @classmethod
    def check_self_citation_ratio(
        cls,
        project_author: str,
        sources: List[dict],
    ) -> Optional[RedFlag]:
        """Check if self-citation ratio is excessive."""
        if not sources:
            return None
        
        author_normalized = project_author.lower().split()[-1]
        
        self_citations = 0
        for source in sources:
            authors = source.get("authors", [])
            if any(author_normalized in a.lower() for a in authors):
                self_citations += 1
        
        ratio = self_citations / len(sources)
        
        if ratio > cls.MAX_SELF_CITATION_RATIO:
            return RedFlag(
                flag_type=RedFlagType.SELF_CITATION_EXCESSIVE,
                source_id=uuid.uuid4(),  # Project-level flag
                severity="medium",
                message=f"Self-citation ratio ({ratio:.0%}) exceeds threshold ({cls.MAX_SELF_CITATION_RATIO:.0%})",
                details={
                    "self_citations": self_citations,
                    "total_sources": len(sources),
                    "ratio": ratio,
                },
                blocks_export=False,  # Warning only
            )
        
        return None
    
    @classmethod
    def aggregate_flags(
        cls,
        source_id: uuid.UUID,
        cited_data: dict,
        api_metadata: Optional[SourceMetadata],
        api_found: bool,
    ) -> List[RedFlag]:
        """Run all red flag checks on a source."""
        flags = []
        
        # Check existence
        if flag := cls.check_existence_failure(
            source_id,
            cited_data.get("doi"),
            api_found,
        ):
            flags.append(flag)
        
        # Check date
        if api_metadata:
            flag = cls.check_date_mismatch(
                source_id,
                cited_data.get("year"),
                api_metadata.year,
            )
            if flag:
                flags.append(flag)

        # Check authors
        if api_metadata and api_metadata.authors:
            flag = cls.check_author_mismatch(
                source_id,
                cited_data.get("authors", []),
                api_metadata.authors,
            )
            if flag:
                flags.append(flag)
        
        # Check suspicious patterns
        if flag := cls.check_suspicious_patterns(source_id, cited_data):
            flags.append(flag)
        
        return flags
