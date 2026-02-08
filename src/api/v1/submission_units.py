"""Submission unit endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, and_

from src.api.deps import DbSession, CurrentUser, RequireProjectView, RequireProjectEdit, get_client_ip
from src.schemas.submission_unit import (
    SubmissionUnitCreate,
    SubmissionUnitUpdate,
    SubmissionUnitStateTransition,
    SubmissionUnitResponse,
)
from src.kernel.models.submission_unit import SubmissionUnit, SubmissionUnitState
from src.kernel.models.project import ResearchProject
from src.kernel.models.artifact import Artifact
from src.kernel.models.user import UserRole
from src.orchestration.state_machine import StateMachine, can_transition, valid_transitions

router = APIRouter()


@router.get("/projects/{project_id}/submission-units", response_model=list[SubmissionUnitResponse])
async def list_submission_units(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """List submission units for a project."""
    q = select(SubmissionUnit).where(
        and_(
            SubmissionUnit.project_id == project_id,
        )
    )
    result = await db.execute(q)
    units = result.scalars().all()
    return [
        SubmissionUnitResponse(
            id=u.id,
            project_id=u.project_id,
            title=u.title,
            artifact_ids=[str(aid) for aid in (u.artifact_ids or [])],
            state=u.state.value,
            state_changed_at=u.state_changed_at,
            state_changed_by=u.state_changed_by,
            current_review_request_id=u.current_review_request_id,
            last_approved_at=u.last_approved_at,
            approval_version=u.approval_version,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in units
    ]


@router.post("/projects/{project_id}/submission-units", response_model=SubmissionUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_submission_unit(
    project_id: uuid.UUID,
    data: SubmissionUnitCreate,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
):
    """Create a submission unit."""
    q = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(q)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    unit = SubmissionUnit(
        project_id=project_id,
        title=data.title,
        artifact_ids=[str(aid) for aid in (data.artifact_ids or [])] if data.artifact_ids else [],
        state=SubmissionUnitState.DRAFT,
    )
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    state_val = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
    return SubmissionUnitResponse(
        id=unit.id,
        project_id=unit.project_id,
        title=unit.title,
        artifact_ids=[str(aid) for aid in (unit.artifact_ids or [])],
        state=state_val,
        state_changed_at=unit.state_changed_at,
        state_changed_by=unit.state_changed_by,
        current_review_request_id=unit.current_review_request_id,
        last_approved_at=unit.last_approved_at,
        approval_version=unit.approval_version,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.get("/projects/{project_id}/submission-units/{unit_id}", response_model=SubmissionUnitResponse)
async def get_submission_unit(
    project_id: uuid.UUID,
    unit_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get a submission unit."""
    q = select(SubmissionUnit).where(
        and_(
            SubmissionUnit.id == unit_id,
            SubmissionUnit.project_id == project_id,
        )
    )
    result = await db.execute(q)
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Submission unit not found")
    state_val = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
    return SubmissionUnitResponse(
        id=unit.id,
        project_id=unit.project_id,
        title=unit.title,
        artifact_ids=[str(aid) for aid in (unit.artifact_ids or [])],
        state=state_val,
        state_changed_at=unit.state_changed_at,
        state_changed_by=unit.state_changed_by,
        current_review_request_id=unit.current_review_request_id,
        last_approved_at=unit.last_approved_at,
        approval_version=unit.approval_version,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.patch("/projects/{project_id}/submission-units/{unit_id}/state", response_model=SubmissionUnitResponse)
async def transition_submission_unit_state(
    request: Request,
    project_id: uuid.UUID,
    unit_id: uuid.UUID,
    data: SubmissionUnitStateTransition,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
):
    """Transition submission unit state (student/advisor)."""
    q = select(SubmissionUnit).where(
        and_(
            SubmissionUnit.id == unit_id,
            SubmissionUnit.project_id == project_id,
        )
    )
    result = await db.execute(q)
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Submission unit not found")

    from_state = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
    if not can_transition(user.role, from_state, data.to_state, "submission_unit"):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot transition from {from_state} to {data.to_state}",
        )

    sm = StateMachine(db)
    await sm.transition_unit(
        unit=unit,
        to_state=data.to_state,
        user_id=user.id,
        user_role=user.role,
        ip_address=get_client_ip(request),
    )
    await db.flush()
    await db.refresh(unit)
    state_val = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
    return SubmissionUnitResponse(
        id=unit.id,
        project_id=unit.project_id,
        title=unit.title,
        artifact_ids=[str(aid) for aid in (unit.artifact_ids or [])],
        state=state_val,
        state_changed_at=unit.state_changed_at,
        state_changed_by=unit.state_changed_by,
        current_review_request_id=unit.current_review_request_id,
        last_approved_at=unit.last_approved_at,
        approval_version=unit.approval_version,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )
