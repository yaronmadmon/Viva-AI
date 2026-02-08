"""
Layer 4: Cross-Project Warnings - Detect conflicting interpretations.

Checks if the same source is used differently across projects,
flagging potential inconsistencies.
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.validation.format_validator import ValidationResult, ValidationStatus
from src.kernel.models.artifact import Artifact, Source
from src.kernel.models.project import ResearchProject


class ConflictingInterpretation(BaseModel):
    """A conflicting interpretation of the same source."""

    source_id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    interpretation: str
    author_id: uuid.UUID


class CrossProjectChecker:
    """
    Layer 4: Cross-project conflict detection.
    Flags when the same source (by DOI/ISBN) is used in other projects.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_uses_of_source(
        self,
        doi: Optional[str] = None,
        isbn: Optional[str] = None,
    ) -> List[ConflictingInterpretation]:
        """
        Get all uses of a source across all projects.
        Query Source joined with Artifact (and project for owner_id).
        """
        if not doi and not isbn:
            return []

        q = (
            select(Source, Artifact, ResearchProject)
            .join(Artifact, Source.artifact_id == Artifact.id)
            .join(ResearchProject, Artifact.project_id == ResearchProject.id)
        )
        if doi:
            q = q.where(Source.doi == doi)
        else:
            q = q.where(Source.isbn == isbn)
        q = q.where(Artifact.deleted_at.is_(None))

        result = await self.session.execute(q)
        rows = result.all()

        out: List[ConflictingInterpretation] = []
        for source, artifact, project in rows:
            interpretation = (artifact.content or "")[:500]
            if not interpretation and isinstance(source.citation_data, dict):
                interpretation = str(source.citation_data.get("title", ""))[:500]
            out.append(
                ConflictingInterpretation(
                    source_id=source.id,
                    project_id=artifact.project_id,
                    artifact_id=artifact.id,
                    interpretation=interpretation or "(no content)",
                    author_id=project.owner_id,
                )
            )
        return out

    async def check_for_conflicts(
        self,
        source_doi: Optional[str],
        source_isbn: Optional[str],
        current_project_id: uuid.UUID,
        current_interpretation: str,
    ) -> tuple[ValidationResult, List[ConflictingInterpretation]]:
        """
        Check if source is used in other projects; if so, return WARNING and list of conflicts.
        """
        all_uses = await self.get_all_uses_of_source(doi=source_doi, isbn=source_isbn)
        conflicts = [u for u in all_uses if u.project_id != current_project_id]

        if conflicts:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=4,
                    message=f"Source used in {len(conflicts)} other project(s)",
                    details={"conflict_count": len(conflicts)},
                ),
                conflicts,
            )
        return (
            ValidationResult(
                status=ValidationStatus.VALID,
                layer=4,
                message="No cross-project conflicts detected",
            ),
            [],
        )
