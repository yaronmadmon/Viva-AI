"""
Quality Audit API – exposes the Harvard-level quality engines via REST.

Endpoints:
  POST /projects/{project_id}/quality/claim-audit
  POST /projects/{project_id}/quality/methodology-stress-test
  POST /projects/{project_id}/quality/contribution-check
  POST /projects/{project_id}/quality/literature-tension
  POST /projects/{project_id}/quality/pedagogical-annotations
  GET  /projects/{project_id}/quality/full-report
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_

from src.api.deps import CurrentUser, DbSession, RequireProjectView
from src.kernel.models.artifact import Artifact
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ── Request / Response schemas ───────────────────────────────────────────

class TextAuditRequest(BaseModel):
    """Audit a block of text (or pull from an artifact)."""
    text: Optional[str] = Field(None, description="Raw text to audit. If not provided, uses artifact_id.")
    artifact_id: Optional[str] = Field(None, description="Artifact ID to audit.")
    section_title: str = ""


class ClaimAuditResponse(BaseModel):
    section_title: str
    total_sentences: int
    descriptive_count: int
    inferential_count: int
    speculative_count: int
    overreach_count: int
    unhedged_inferential_count: int
    certainty_score: float
    passed: bool
    flags: List[Dict[str, Any]]


class MethodologyStressResponse(BaseModel):
    has_rejected_alternatives: bool
    has_failure_conditions: bool
    has_boundary_conditions: bool
    has_justification: bool
    procedural_ratio: float
    defensibility_score: float
    passed: bool
    examiner_questions: List[Dict[str, Any]]
    flags: List[Dict[str, Any]]


class ContributionCheckResponse(BaseModel):
    claim_count: int
    has_before_after: bool
    has_falsifiability: bool
    broad_claim_count: int
    precision_score: float
    passed: bool
    flags: List[Dict[str, Any]]


class LiteratureTensionResponse(BaseModel):
    total_paragraphs: int
    named_disagreement_count: int
    vague_attribution_count: int
    tension_style_count: int
    synthesis_count: int
    tension_score: float
    passed: bool
    named_disagreements: List[Dict[str, Any]]
    flags: List[Dict[str, Any]]


class PedagogicalAnnotationResponse(BaseModel):
    section_title: str
    total_paragraphs: int
    annotation_count: int
    model_used: str
    annotations: List[Dict[str, Any]]


class FullQualityReportResponse(BaseModel):
    project_id: str
    sections_audited: int
    claim_audit: Optional[ClaimAuditResponse] = None
    methodology_stress: Optional[MethodologyStressResponse] = None
    contribution_check: Optional[ContributionCheckResponse] = None
    literature_tension: Optional[LiteratureTensionResponse] = None
    overall_score: float
    passed: bool
    summary: str


# ── Helper: get text from request ────────────────────────────────────────

async def _get_text(body: TextAuditRequest, db: DbSession, project_id: uuid.UUID) -> str:
    """Resolve text from body.text or body.artifact_id."""
    if body.text:
        return body.text

    if body.artifact_id:
        artifact = await db.get(Artifact, uuid.UUID(body.artifact_id))
        if not artifact or artifact.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")
        return artifact.content or ""

    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide text or artifact_id")


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/quality/claim-audit",
    response_model=ClaimAuditResponse,
)
async def claim_audit(
    project_id: uuid.UUID,
    body: TextAuditRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Run claim discipline audit on a section of text."""
    from src.engines.validation.claim_classifier import deep_audit_section

    text = await _get_text(body, db, project_id)
    result = await deep_audit_section(text, body.section_title)

    return ClaimAuditResponse(
        section_title=result.section_title,
        total_sentences=result.total_sentences,
        descriptive_count=result.descriptive_count,
        inferential_count=result.inferential_count,
        speculative_count=result.speculative_count,
        overreach_count=result.overreach_count,
        unhedged_inferential_count=result.unhedged_inferential_count,
        certainty_score=result.certainty_score,
        passed=result.passed,
        flags=[
            {
                "sentence": f.sentence,
                "level": f.level.value,
                "issue": f.issue,
                "severity": f.severity,
                "suggestion": f.suggestion,
                "line_hint": f.line_hint,
            }
            for f in result.flags
        ],
    )


@router.post(
    "/projects/{project_id}/quality/methodology-stress-test",
    response_model=MethodologyStressResponse,
)
async def methodology_stress_test(
    project_id: uuid.UUID,
    body: TextAuditRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Run methodology stress test on the methodology section."""
    from src.engines.validation.methodology_stress_test import deep_stress_test_methodology

    text = await _get_text(body, db, project_id)
    result = await deep_stress_test_methodology(text)

    return MethodologyStressResponse(
        has_rejected_alternatives=result.has_rejected_alternatives,
        has_failure_conditions=result.has_failure_conditions,
        has_boundary_conditions=result.has_boundary_conditions,
        has_justification=result.has_justification,
        procedural_ratio=result.procedural_ratio,
        defensibility_score=result.defensibility_score,
        passed=result.passed,
        examiner_questions=[
            {
                "question": q.question,
                "category": q.category,
                "expected_elements": q.expected_elements,
            }
            for q in result.examiner_questions
        ],
        flags=[
            {
                "issue": f.issue,
                "severity": f.severity,
                "category": f.category,
                "suggestion": f.suggestion,
            }
            for f in result.flags
        ],
    )


@router.post(
    "/projects/{project_id}/quality/contribution-check",
    response_model=ContributionCheckResponse,
)
async def contribution_check(
    project_id: uuid.UUID,
    body: TextAuditRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Validate the contribution statement in the conclusion."""
    from src.engines.validation.contribution_checker import deep_audit_contribution

    text = await _get_text(body, db, project_id)
    result = await deep_audit_contribution(text)

    return ContributionCheckResponse(
        claim_count=result.claim_count,
        has_before_after=result.has_before_after,
        has_falsifiability=result.has_falsifiability,
        broad_claim_count=result.broad_claim_count,
        precision_score=result.precision_score,
        passed=result.passed,
        flags=[
            {
                "issue": f.issue,
                "severity": f.severity,
                "text_excerpt": f.text_excerpt,
                "suggestion": f.suggestion,
            }
            for f in result.flags
        ],
    )


@router.post(
    "/projects/{project_id}/quality/literature-tension",
    response_model=LiteratureTensionResponse,
)
async def literature_tension(
    project_id: uuid.UUID,
    body: TextAuditRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Assess literature review tension and named disagreements."""
    from src.engines.validation.literature_tension_checker import deep_audit_literature_tension

    text = await _get_text(body, db, project_id)
    result = await deep_audit_literature_tension(text)

    return LiteratureTensionResponse(
        total_paragraphs=result.total_paragraphs,
        named_disagreement_count=len(result.named_disagreements),
        vague_attribution_count=result.vague_attribution_count,
        tension_style_count=result.tension_style_count,
        synthesis_count=result.synthesis_count,
        tension_score=result.tension_score,
        passed=result.passed,
        named_disagreements=[
            {
                "author_a": d.author_a,
                "year_a": d.year_a,
                "author_b": d.author_b,
                "year_b": d.year_b,
                "context": d.context[:200],
            }
            for d in result.named_disagreements
        ],
        flags=[
            {
                "issue": f.issue,
                "severity": f.severity,
                "text_excerpt": f.text_excerpt,
                "suggestion": f.suggestion,
            }
            for f in result.flags
        ],
    )


@router.post(
    "/projects/{project_id}/quality/pedagogical-annotations",
    response_model=PedagogicalAnnotationResponse,
)
async def pedagogical_annotations(
    project_id: uuid.UUID,
    body: TextAuditRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Generate pedagogical annotations for a section."""
    from src.engines.validation.pedagogical_annotator import annotate_section_deep

    text = await _get_text(body, db, project_id)
    result = await annotate_section_deep(text, body.section_title)

    return PedagogicalAnnotationResponse(
        section_title=result.section_title,
        total_paragraphs=result.total_paragraphs,
        annotation_count=len(result.annotations),
        model_used=result.model_used,
        annotations=[
            {
                "id": a.id,
                "type": a.annotation_type,
                "paragraph_index": a.paragraph_index,
                "explanation": a.explanation,
                "examiner_concern": a.examiner_concern,
            }
            for a in result.annotations
        ],
    )


@router.get(
    "/projects/{project_id}/quality/full-report",
    response_model=FullQualityReportResponse,
)
async def full_quality_report(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """
    Run ALL quality engines on the project's sections and return
    a comprehensive quality report.
    """
    from src.engines.validation.claim_classifier import audit_section
    from src.engines.validation.methodology_stress_test import stress_test_methodology
    from src.engines.validation.contribution_checker import audit_contribution
    from src.engines.validation.literature_tension_checker import audit_literature_tension

    # Fetch all non-deleted artifacts
    q = select(Artifact).where(
        and_(
            Artifact.project_id == project_id,
            Artifact.deleted_at.is_(None),
        )
    )
    result = await db.execute(q)
    artifacts = result.scalars().all()

    if not artifacts:
        return FullQualityReportResponse(
            project_id=str(project_id),
            sections_audited=0,
            overall_score=0,
            passed=False,
            summary="No artifacts found. Add content to generate a quality report.",
        )

    # Categorize artifacts by section type / title
    all_text = ""
    lit_review_text = ""
    methodology_text = ""
    conclusion_text = ""
    sections_count = 0

    for a in artifacts:
        content = a.content or ""
        title = (a.title or "").lower()
        all_text += content + "\n\n"
        sections_count += 1

        if "literature" in title or "review" in title:
            lit_review_text += content + "\n\n"
        elif "method" in title:
            methodology_text += content + "\n\n"
        elif "conclusion" in title:
            conclusion_text += content + "\n\n"

    # Run engines (rule-based for speed on full report)
    claim_result = audit_section(all_text, "Full Dissertation") if all_text.strip() else None
    method_result = stress_test_methodology(methodology_text) if methodology_text.strip() else None
    contrib_result = audit_contribution(conclusion_text) if conclusion_text.strip() else None
    tension_result = audit_literature_tension(lit_review_text) if lit_review_text.strip() else None

    # Compute overall score (weighted average)
    scores = []
    if claim_result:
        # Invert certainty: lower certainty = better claim discipline
        scores.append(("claim", max(0, 100 - claim_result.certainty_score), 30))
    if method_result:
        scores.append(("method", method_result.defensibility_score, 25))
    if contrib_result:
        scores.append(("contribution", contrib_result.precision_score, 25))
    if tension_result:
        scores.append(("tension", tension_result.tension_score, 20))

    total_weight = sum(w for _, _, w in scores)
    overall = sum(s * w for _, s, w in scores) / total_weight if total_weight else 0

    passed = all([
        claim_result.passed if claim_result else False,
        method_result.passed if method_result else False,
        contrib_result.passed if contrib_result else False,
        tension_result.passed if tension_result else False,
    ])

    # Build summary
    parts = []
    if claim_result:
        parts.append(f"Claim discipline: {100 - claim_result.certainty_score:.0f}/100 "
                      f"({'PASS' if claim_result.passed else 'NEEDS WORK'})")
    if method_result:
        parts.append(f"Methodology defensibility: {method_result.defensibility_score:.0f}/100 "
                      f"({'PASS' if method_result.passed else 'NEEDS WORK'})")
    if contrib_result:
        parts.append(f"Contribution precision: {contrib_result.precision_score:.0f}/100 "
                      f"({'PASS' if contrib_result.passed else 'NEEDS WORK'})")
    if tension_result:
        parts.append(f"Literature tension: {tension_result.tension_score:.0f}/100 "
                      f"({'PASS' if tension_result.passed else 'NEEDS WORK'})")

    # Build response
    claim_resp = None
    if claim_result:
        claim_resp = ClaimAuditResponse(
            section_title=claim_result.section_title,
            total_sentences=claim_result.total_sentences,
            descriptive_count=claim_result.descriptive_count,
            inferential_count=claim_result.inferential_count,
            speculative_count=claim_result.speculative_count,
            overreach_count=claim_result.overreach_count,
            unhedged_inferential_count=claim_result.unhedged_inferential_count,
            certainty_score=claim_result.certainty_score,
            passed=claim_result.passed,
            flags=[{"sentence": f.sentence, "level": f.level.value, "issue": f.issue,
                    "severity": f.severity, "suggestion": f.suggestion}
                   for f in claim_result.flags[:20]],
        )

    method_resp = None
    if method_result:
        method_resp = MethodologyStressResponse(
            has_rejected_alternatives=method_result.has_rejected_alternatives,
            has_failure_conditions=method_result.has_failure_conditions,
            has_boundary_conditions=method_result.has_boundary_conditions,
            has_justification=method_result.has_justification,
            procedural_ratio=method_result.procedural_ratio,
            defensibility_score=method_result.defensibility_score,
            passed=method_result.passed,
            examiner_questions=[{"question": q.question, "category": q.category}
                                for q in method_result.examiner_questions],
            flags=[{"issue": f.issue, "severity": f.severity, "category": f.category,
                    "suggestion": f.suggestion} for f in method_result.flags],
        )

    contrib_resp = None
    if contrib_result:
        contrib_resp = ContributionCheckResponse(
            claim_count=contrib_result.claim_count,
            has_before_after=contrib_result.has_before_after,
            has_falsifiability=contrib_result.has_falsifiability,
            broad_claim_count=contrib_result.broad_claim_count,
            precision_score=contrib_result.precision_score,
            passed=contrib_result.passed,
            flags=[{"issue": f.issue, "severity": f.severity, "text_excerpt": f.text_excerpt,
                    "suggestion": f.suggestion} for f in contrib_result.flags],
        )

    tension_resp = None
    if tension_result:
        tension_resp = LiteratureTensionResponse(
            total_paragraphs=tension_result.total_paragraphs,
            named_disagreement_count=len(tension_result.named_disagreements),
            vague_attribution_count=tension_result.vague_attribution_count,
            tension_style_count=tension_result.tension_style_count,
            synthesis_count=tension_result.synthesis_count,
            tension_score=tension_result.tension_score,
            passed=tension_result.passed,
            named_disagreements=[
                {"author_a": d.author_a, "author_b": d.author_b, "context": d.context[:200]}
                for d in tension_result.named_disagreements
            ],
            flags=[{"issue": f.issue, "severity": f.severity, "suggestion": f.suggestion}
                   for f in tension_result.flags],
        )

    return FullQualityReportResponse(
        project_id=str(project_id),
        sections_audited=sections_count,
        claim_audit=claim_resp,
        methodology_stress=method_resp,
        contribution_check=contrib_resp,
        literature_tension=tension_resp,
        overall_score=round(overall, 1),
        passed=passed,
        summary=" | ".join(parts) if parts else "No sections to audit.",
    )
