"""
Validation Service - Orchestrates 5-layer citation verification.
"""

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.validation.format_validator import FormatValidator, ValidationResult, ValidationStatus
from src.engines.validation.existence_checker import ExistenceChecker, SourceMetadata
from src.engines.validation.content_verifier import ContentVerifier, ContentVerificationRequest
from src.engines.validation.cross_project_checker import CrossProjectChecker, ConflictingInterpretation
from src.engines.validation.red_flag_detector import RedFlagDetector, RedFlag
from src.kernel.models.artifact import Artifact, ArtifactType, Source


class FullValidationResult(BaseModel):
    """Complete validation result across all layers."""
    
    source_id: uuid.UUID
    
    # Layer results
    format_results: List[ValidationResult]
    existence_result: Optional[ValidationResult] = None
    content_checks_required: List[ContentVerificationRequest] = []
    cross_project_result: Optional[ValidationResult] = None
    red_flags: List[RedFlag] = []
    
    # Retrieved metadata
    api_metadata: Optional[SourceMetadata] = None
    
    # Overall status
    overall_status: ValidationStatus
    blocks_export: bool
    message: str


class ValidationService:
    """
    Orchestrates 5-layer citation verification.
    
    Usage:
        service = ValidationService(session)
        result = await service.validate_source(source_id, citation_data)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cross_project_checker = CrossProjectChecker(session)
    
    async def validate_source(
        self,
        source_id: uuid.UUID,
        citation_data: Dict[str, Any],
        project_id: uuid.UUID,
        run_api_checks: bool = True,
    ) -> FullValidationResult:
        """
        Run full 5-layer validation on a source.
        
        Args:
            source_id: The source artifact ID
            citation_data: Citation metadata (doi, isbn, authors, year, etc.)
            project_id: Current project ID (for cross-project checks)
            run_api_checks: Whether to run Layer 2 API checks
            
        Returns:
            Complete validation result
        """
        format_results = []
        existence_result = None
        api_metadata = None
        content_checks = []
        cross_project_result = None
        red_flags = []
        
        # Layer 1: Format validation
        if doi := citation_data.get("doi"):
            format_results.append(FormatValidator.validate_doi(doi))
        
        if isbn := citation_data.get("isbn"):
            format_results.append(FormatValidator.validate_isbn(isbn))
        
        if arxiv := citation_data.get("arxiv"):
            format_results.append(FormatValidator.validate_arxiv(arxiv))
        
        if year := citation_data.get("year"):
            format_results.append(FormatValidator.validate_year(year))
        
        source_type = citation_data.get("type", "journal")
        format_results.extend(
            FormatValidator.validate_required_fields(source_type, citation_data)
        )
        
        # Check if Layer 1 passed
        layer1_passed = all(r.status != ValidationStatus.INVALID for r in format_results)
        
        # Layer 2: Existence check (if Layer 1 passed and enabled)
        api_found = False
        if layer1_passed and run_api_checks:
            if doi := citation_data.get("doi"):
                existence_result, api_metadata = await ExistenceChecker.verify_doi(doi)
                api_found = existence_result.status == ValidationStatus.VALID
            elif isbn := citation_data.get("isbn"):
                existence_result, api_metadata = await ExistenceChecker.verify_isbn(isbn)
                api_found = existence_result.status == ValidationStatus.VALID
            elif arxiv := citation_data.get("arxiv"):
                existence_result, api_metadata = await ExistenceChecker.verify_arxiv(arxiv)
                api_found = existence_result.status == ValidationStatus.VALID
        
        # Layer 3: Content verification requests (if mismatches detected)
        if api_metadata:
            # Check for author mismatch
            cited_authors = citation_data.get("authors", [])
            if api_metadata.authors and cited_authors:
                # Simple check - if names don't match, request verification
                cited_names = set(a.lower() for a in cited_authors)
                api_names = set(a.lower() for a in api_metadata.authors)
                if not cited_names & api_names:
                    content_checks.append(
                        ContentVerifier.create_author_check(
                            source_id,
                            source_id,  # Placeholder claim_id
                            str(cited_authors),
                            str(api_metadata.authors),
                        )
                    )
            
            # Check for year mismatch
            cited_year = citation_data.get("year")
            if cited_year and api_metadata.year and cited_year != api_metadata.year:
                content_checks.append(
                    ContentVerifier.create_date_check(
                        source_id,
                        source_id,
                        cited_year,
                        api_metadata.year,
                    )
                )
        
        # Layer 4: Cross-project check
        cross_project_result, conflicts = await self.cross_project_checker.check_for_conflicts(
            citation_data.get("doi"),
            citation_data.get("isbn"),
            project_id,
            citation_data.get("interpretation", ""),
        )
        
        # Layer 5: Red flag detection
        red_flags = RedFlagDetector.aggregate_flags(
            source_id,
            citation_data,
            api_metadata,
            api_found,
        )
        
        # Determine overall status
        has_invalid = any(r.status == ValidationStatus.INVALID for r in format_results)
        has_blocking_flags = any(f.blocks_export for f in red_flags)
        has_warnings = (
            any(r.status == ValidationStatus.WARNING for r in format_results) or
            (existence_result and existence_result.status == ValidationStatus.WARNING) or
            (cross_project_result and cross_project_result.status == ValidationStatus.WARNING) or
            any(not f.blocks_export for f in red_flags)
        )
        
        if has_invalid or has_blocking_flags:
            overall_status = ValidationStatus.INVALID
            blocks_export = True
            message = "Critical validation issues detected"
        elif has_warnings:
            overall_status = ValidationStatus.WARNING
            blocks_export = False
            message = "Validation passed with warnings"
        else:
            overall_status = ValidationStatus.VALID
            blocks_export = False
            message = "All validation checks passed"
        
        return FullValidationResult(
            source_id=source_id,
            format_results=format_results,
            existence_result=existence_result,
            content_checks_required=content_checks,
            cross_project_result=cross_project_result,
            red_flags=red_flags,
            api_metadata=api_metadata,
            overall_status=overall_status,
            blocks_export=blocks_export,
            message=message,
        )
    
    async def validate_all_sources_in_project(
        self,
        project_id: uuid.UUID,
        run_api_checks: bool = True,
    ) -> Dict[uuid.UUID, FullValidationResult]:
        """
        Validate all sources in a project.
        Queries all Source artifacts for the project and runs full validation on each.
        """
        q = (
            select(Source, Artifact)
            .join(Artifact, Source.artifact_id == Artifact.id)
            .where(
                and_(
                    Artifact.project_id == project_id,
                    Artifact.artifact_type == ArtifactType.SOURCE,
                    Artifact.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.execute(q)
        rows = result.all()

        results: Dict[uuid.UUID, FullValidationResult] = {}
        for source, artifact in rows:
            citation_data = source.citation_data if isinstance(source.citation_data, dict) else {}
            if source.doi:
                citation_data = {**citation_data, "doi": source.doi}
            if source.isbn:
                citation_data = {**citation_data, "isbn": source.isbn}
            full = await self.validate_source(
                source_id=artifact.id,
                citation_data=citation_data,
                project_id=project_id,
                run_api_checks=run_api_checks,
            )
            results[artifact.id] = full
        return results
