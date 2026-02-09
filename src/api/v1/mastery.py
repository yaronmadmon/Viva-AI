"""
Mastery endpoints - progress, checkpoints, capabilities, AI suggestions.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_

from src.api.deps import CurrentUser, DbSession, RequireProjectView
from src.engines.mastery.ai_disclosure_controller import (
    AICapability,
    AIDisclosureController,
)
from src.engines.mastery.checkpoint_service import (
    CheckpointService,
    CheckpointType,
    QuestionResult,
)
from src.engines.mastery.grader import Grader
from src.engines.mastery.progress_tracker import ProgressTracker
from src.engines.mastery.question_bank import QuestionBank
from src.kernel.models.artifact import Artifact
from src.kernel.models.permission import PermissionLevel
from src.kernel.permissions.permission_service import PermissionService
from src.kernel.events.event_store import log_ai_suggestion
from src.schemas.ai_suggestion import (
    AISuggestionAcceptRequest,
    AISuggestionGenerateRequest,
    AISuggestionGenerateResponse,
    AISuggestionRejectRequest,
)
from src.schemas.mastery import (
    CapabilitiesResponse,
    CapabilityItem,
    CapabilityRequestResponse,
    CheckpointAttemptSummary,
    CheckpointQuestionSchema,
    CheckpointResultResponse,
    CheckpointStartResponse,
    CheckpointSubmitRequest,
    MasteryProgressResponse,
    QuestionResultResponse,
)

router = APIRouter()


def _enum_val(e) -> str:
    """Safely get enum value (SQLite may return str)."""
    return e.value if hasattr(e, "value") else str(e)


def _question_to_schema(q) -> CheckpointQuestionSchema:
    return CheckpointQuestionSchema(
        id=q.id,
        question_type=_enum_val(q.question_type),
        text=q.text,
        options=q.options,
        topic=q.topic,
        difficulty=q.difficulty,
        grading_rubric=q.grading_rubric,
    )


@router.get("/progress", response_model=MasteryProgressResponse)
async def get_mastery_progress(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get current user's mastery status for the project."""
    tracker = ProgressTracker(db)
    progress = await tracker.get_progress(user.id, project_id)
    next_cp = await tracker.get_next_checkpoint(user.id, project_id)
    return MasteryProgressResponse(
        current_tier=progress.current_tier,
        ai_level=progress.ai_level,
        total_words_written=progress.total_words_written,
        next_checkpoint=_enum_val(next_cp) if next_cp else None,
        attempts=[
            CheckpointAttemptSummary(
                checkpoint_type=_enum_val(a.checkpoint_type),
                passed=a.passed,
                score=a.score_percentage,
                completed_at=a.completed_at,
            )
            for a in progress.checkpoint_attempts
        ],
    )


@router.post("/checkpoint/{tier}/start", response_model=CheckpointStartResponse)
async def start_checkpoint(
    project_id: uuid.UUID,
    tier: int,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get questions for a checkpoint attempt. Tier 1, 2, or 3."""
    if tier == 1:
        checkpoint_type = CheckpointType.TIER_1_COMPREHENSION
        questions = QuestionBank.get_tier_1_questions(count=CheckpointService.TIER_1_QUESTION_COUNT)
        required = CheckpointService.TIER_1_QUESTION_COUNT
        desc = "80% correct (4/5)"
    elif tier == 2:
        checkpoint_type = CheckpointType.TIER_2_ANALYSIS
        questions = QuestionBank.get_tier_2_prompts(count=CheckpointService.TIER_2_PROMPT_COUNT)
        required = CheckpointService.TIER_2_PROMPT_COUNT
        desc = "150 words minimum per prompt (3 prompts)"
    elif tier == 3:
        checkpoint_type = CheckpointType.TIER_3_DEFENSE
        questions = QuestionBank.get_tier_3_questions(count=CheckpointService.TIER_3_QUESTION_COUNT)
        required = CheckpointService.TIER_3_QUESTION_COUNT
        desc = "85% correct (9/10)"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tier must be 1, 2, or 3")
    return CheckpointStartResponse(
        tier=tier,
        checkpoint_type=_enum_val(checkpoint_type),
        questions=[_question_to_schema(q) for q in questions],
        required_count=required,
        pass_threshold_description=desc,
    )


@router.post("/checkpoint/{tier}/submit", response_model=CheckpointResultResponse)
async def submit_checkpoint(
    project_id: uuid.UUID,
    tier: int,
    body: CheckpointSubmitRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Submit checkpoint answers and get result."""
    if tier == 1:
        checkpoint_type = CheckpointType.TIER_1_COMPREHENSION
        questions = QuestionBank.get_tier_1_questions(count=CheckpointService.TIER_1_QUESTION_COUNT)
    elif tier == 2:
        checkpoint_type = CheckpointType.TIER_2_ANALYSIS
        questions = QuestionBank.get_tier_2_prompts(count=CheckpointService.TIER_2_PROMPT_COUNT)
    elif tier == 3:
        checkpoint_type = CheckpointType.TIER_3_DEFENSE
        questions = QuestionBank.get_tier_3_questions(count=CheckpointService.TIER_3_QUESTION_COUNT)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tier must be 1, 2, or 3")

    q_by_id = {q.id: q for q in questions}
    results: List[QuestionResult] = []
    for item in body.answers:
        q = q_by_id.get(item.question_id)
        if not q:
            continue
        if tier == 2:
            res = Grader.grade_tier_2_response(q, item.user_answer)
        else:
            res = Grader.grade(q, item.user_answer, item.word_count)
        results.append(res)

    tracker = ProgressTracker(db)
    attempt_number = await tracker.get_attempt_count(user.id, project_id, checkpoint_type) + 1
    time_spent = body.time_spent_seconds

    if tier == 1:
        cr = CheckpointService.evaluate_tier_1(user.id, project_id, results, attempt_number, time_spent)
    elif tier == 2:
        cr = CheckpointService.evaluate_tier_2(user.id, project_id, results, attempt_number, time_spent)
    else:
        cr = CheckpointService.evaluate_tier_3(user.id, project_id, results, attempt_number, time_spent)

    await tracker.record_checkpoint_result(cr)

    return CheckpointResultResponse(
        checkpoint_type=_enum_val(cr.checkpoint_type),
        total_questions=cr.total_questions,
        correct_answers=cr.correct_answers,
        score_percentage=cr.score_percentage,
        passed=cr.passed,
        question_results=[
            QuestionResultResponse(
                question_id=r.question_id,
                correct=r.correct,
                user_answer=r.user_answer,
                word_count=r.word_count,
            )
            for r in cr.question_results
        ],
        attempt_number=cr.attempt_number,
        tier_unlocked=cr.tier_unlocked,
        ai_level_unlocked=cr.ai_level_unlocked,
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get available AI capabilities for the user's level in this project."""
    tracker = ProgressTracker(db)
    progress = await tracker.get_progress(user.id, project_id)
    caps = AIDisclosureController.get_available_capabilities(progress.ai_level)
    level_desc = AIDisclosureController.get_level_description(progress.ai_level)
    next_req = AIDisclosureController.get_next_level_requirements(progress.ai_level)
    return CapabilitiesResponse(
        ai_level=progress.ai_level,
        level_description=level_desc,
        capabilities=[CapabilityItem(capability=_enum_val(c)) for c in caps],
        next_level_requirements=next_req,
    )


@router.post(
    "/ai-suggestions/generate",
    response_model=AISuggestionGenerateResponse,
    summary="Generate an AI suggestion for an artifact",
    description="Capability-gated by suggestion_type. Returns watermarked suggestion content.",
)
async def generate_ai_suggestion(
    project_id: uuid.UUID,
    body: AISuggestionGenerateRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Generate an AI suggestion. Requires project view and the capability for the requested suggestion_type."""
    from src.ai.types import SuggestionType
    from src.ai.sandbox import (
        AISandbox,
        ArtifactContext,
        SuggestionRequest,
    )
    try:
        suggestion_type = SuggestionType(body.suggestion_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown suggestion_type: {body.suggestion_type}",
        )
    q = select(Artifact).where(
        and_(
            Artifact.id == body.artifact_id,
            Artifact.project_id == project_id,
            Artifact.deleted_at.is_(None),
        )
    )
    r = await db.execute(q)
    artifact = r.scalar_one_or_none()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found in this project",
        )
    perm = PermissionService(db)
    if not await perm.check_project_permission(user, project_id, PermissionLevel.VIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    tracker = ProgressTracker(db)
    progress = await tracker.get_progress(user.id, project_id)
    context = ArtifactContext(
        project_id=project_id,
        artifact_id=artifact.id,
        artifact_type=_enum_val(artifact.artifact_type),
        content=artifact.content or "",
        title=artifact.title,
    )
    request = SuggestionRequest(
        user_id=user.id,
        context=context,
        suggestion_type=suggestion_type,
        additional_instructions=body.additional_instructions,
    )
    sandbox = AISandbox()
    output = await sandbox.generate_suggestion(request, progress.ai_level)
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This suggestion type is not unlocked for your AI level. Complete checkpoints to unlock.",
        )
    await log_ai_suggestion(
        db,
        suggestion_id=output.suggestion_id,
        artifact_id=body.artifact_id,
        user_id=user.id,
        suggestion_type=_enum_val(output.suggestion_type),
        action="generated",
    )
    return AISuggestionGenerateResponse(
        suggestion_id=output.suggestion_id,
        suggestion_type=_enum_val(output.suggestion_type),
        content=output.content,
        confidence=output.confidence,
        watermark_hash=output.watermark_hash,
        word_count=output.word_count,
        truncated=output.truncated,
        requires_checkbox=output.requires_checkbox,
        min_modification_required=output.min_modification_required,
        generated_at=output.generated_at,
        model_used=output.model_used,
    )


@router.post(
    "/ai-suggestions/accept",
    summary="Accept an AI suggestion (optionally with user modifications)",
)
async def accept_ai_suggestion(
    project_id: uuid.UUID,
    body: AISuggestionAcceptRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Record that the user accepted a suggestion; used for export integrity and analytics."""
    perm = PermissionService(db)
    if not await perm.check_project_permission(user, project_id, PermissionLevel.EDIT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edit permission required")
    await log_ai_suggestion(
        db,
        suggestion_id=body.suggestion_id,
        artifact_id=body.artifact_id,
        user_id=user.id,
        suggestion_type=body.suggestion_type,
        action="accepted",
        modification_ratio=body.modification_ratio,
    )
    return {"status": "accepted", "suggestion_id": str(body.suggestion_id)}


@router.post(
    "/ai-suggestions/reject",
    summary="Reject an AI suggestion",
)
async def reject_ai_suggestion(
    project_id: uuid.UUID,
    body: AISuggestionRejectRequest,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Record that the user rejected a suggestion."""
    perm = PermissionService(db)
    if not await perm.check_project_permission(user, project_id, PermissionLevel.EDIT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edit permission required")
    await log_ai_suggestion(
        db,
        suggestion_id=body.suggestion_id,
        artifact_id=body.artifact_id,
        user_id=user.id,
        suggestion_type=body.suggestion_type,
        action="rejected",
    )
    return {"status": "rejected", "suggestion_id": str(body.suggestion_id)}


@router.post("/capabilities/{capability}/request", response_model=CapabilityRequestResponse)
async def request_capability(
    project_id: uuid.UUID,
    capability: str,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Check if user can use a capability; returns allowed, reason, restrictions."""
    try:
        cap = AICapability(capability)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown capability: {capability}")
    tracker = ProgressTracker(db)
    progress = await tracker.get_progress(user.id, project_id)
    allowed = AIDisclosureController.has_capability(progress.ai_level, cap)
    restrictions = AIDisclosureController.get_capability_restrictions(cap)
    if allowed:
        reason = "Capability allowed"
    else:
        reason = f"Requires AI level {restrictions.get('min_level', 0)}. Current level: {progress.ai_level}."
    return CapabilityRequestResponse(
        allowed=allowed,
        capability=capability,
        reason=reason,
        restrictions=restrictions,
    )
