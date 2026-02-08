"""
Effort Gate Service - Server-side enforcement of effort thresholds.

Plan: 30min/1000 words, >=3 claim-evidence links, >=200 words notes.
Time-per-words gate requires session/time tracking (TBD); claim-evidence and notes are enforced here.
"""

import uuid
from dataclasses import dataclass
from typing import List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.kernel.models.artifact import (
    Artifact,
    ArtifactLink,
    ArtifactType,
    LinkType,
)


# Thresholds from architecture plan
MIN_CLAIM_EVIDENCE_LINKS = 3
MIN_NOTES_WORDS = 200


@dataclass
class EffortGateResult:
    """Result of checking one effort gate."""
    gate_name: str
    passed: bool
    current: float | int
    required: float | int
    message: str


@dataclass
class EffortGateReport:
    """All effort gates for a project."""
    project_id: uuid.UUID
    all_passed: bool
    gates: List[EffortGateResult]


class EffortGateService:
    """
    Evaluates effort gates for a project.
    Gates: claim-evidence links >= 3, notes words >= 200.
    Time per 1000 words (30 min) deferred until session/time tracking exists.
    """

    @classmethod
    async def check_claim_evidence_links(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        min_links: int = MIN_CLAIM_EVIDENCE_LINKS,
    ) -> EffortGateResult:
        """Count links from CLAIM artifacts to EVIDENCE artifacts (SUPPORTS or CITES)."""
        # Subquery: artifact ids by type for this project
        claim_ids_q = select(Artifact.id).where(
            and_(
                Artifact.project_id == project_id,
                Artifact.artifact_type == ArtifactType.CLAIM,
                Artifact.deleted_at.is_(None),
            )
        )
        evidence_ids_q = select(Artifact.id).where(
            and_(
                Artifact.project_id == project_id,
                Artifact.artifact_type == ArtifactType.EVIDENCE,
                Artifact.deleted_at.is_(None),
            )
        )
        count_q = (
            select(func.count(ArtifactLink.id))
            .where(
                and_(
                    ArtifactLink.source_artifact_id.in_(claim_ids_q.scalar_subquery()),
                    ArtifactLink.target_artifact_id.in_(evidence_ids_q.scalar_subquery()),
                    ArtifactLink.link_type.in_([LinkType.SUPPORTS, LinkType.CITES]),
                )
            )
        )
        result = await db.execute(count_q)
        count = result.scalar() or 0
        passed = count >= min_links
        return EffortGateResult(
            gate_name="claim_evidence_links",
            passed=passed,
            current=count,
            required=min_links,
            message=f"Claim–evidence links: {count}/{min_links}",
        )

    @classmethod
    async def check_notes_words(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        min_words: int = MIN_NOTES_WORDS,
    ) -> EffortGateResult:
        """Total word count in NOTE artifacts."""
        q = select(Artifact).where(
            and_(
                Artifact.project_id == project_id,
                Artifact.artifact_type == ArtifactType.NOTE,
                Artifact.deleted_at.is_(None),
            )
        )
        result = await db.execute(q)
        notes = result.scalars().all()
        word_count = sum(len((a.content or "").split()) for a in notes)
        passed = word_count >= min_words
        return EffortGateResult(
            gate_name="notes_words",
            passed=passed,
            current=word_count,
            required=min_words,
            message=f"Notes word count: {word_count}/{min_words}",
        )

    @classmethod
    async def evaluate_project(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> EffortGateReport:
        """Evaluate all effort gates for a project."""
        link_result = await cls.check_claim_evidence_links(db, project_id)
        notes_result = await cls.check_notes_words(db, project_id)
        gates = [link_result, notes_result]
        all_passed = all(g.passed for g in gates)
        return EffortGateReport(
            project_id=project_id,
            all_passed=all_passed,
            gates=gates,
        )
