"""Examiner endpoints - read-only view of frozen approved content.

Examiners never mutate artifact or SubmissionUnit state.
They only receive frozen approved content and defense answers.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, and_

from src.api.deps import DbSession, CurrentUser
from src.kernel.models.artifact import Artifact
from src.kernel.models.submission_unit import SubmissionUnit, SubmissionUnitState
from src.kernel.models.project import ResearchProject
from src.kernel.models.user import UserRole
from src.kernel.permissions.permission_service import PermissionService
from src.kernel.models.permission import PermissionLevel

router = APIRouter()


def _require_examiner(user: CurrentUser) -> None:
    """Ensure user has examiner role."""
    if user.role != UserRole.EXAMINER and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Examiner role required",
        )


@router.get("/examiner/projects/{project_id}/frozen-content")
async def get_frozen_content(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """
    Get frozen approved content for examination (examiner only).

    Returns locked/approved submission units and their artifacts.
    No comments, drafting history, or state mutation allowed.
    """
    _require_examiner(user)

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

    # List locked or approved units
    q = select(SubmissionUnit).where(
        and_(
            SubmissionUnit.project_id == project_id,
            SubmissionUnit.state.in_([SubmissionUnitState.LOCKED, SubmissionUnitState.APPROVED]),
        )
    )
    result = await db.execute(q)
    units = result.scalars().all()

    units_data = []
    for unit in units:
        unit_state = unit.state.value if hasattr(unit.state, "value") else str(unit.state)
        artifact_ids = unit.artifact_ids or []
        artifacts_data = []
        for aid_str in artifact_ids:
            try:
                aid = uuid.UUID(aid_str) if isinstance(aid_str, str) else aid_str
            except (ValueError, TypeError):
                continue
            aq = select(Artifact).where(
                and_(
                    Artifact.id == aid,
                    Artifact.deleted_at.is_(None),
                )
            )
            ar = await db.execute(aq)
            art = ar.scalar_one_or_none()
            if art:
                artifacts_data.append({
                    "id": str(art.id),
                    "title": art.title,
                    "content": art.content,
                    "artifact_type": art.artifact_type.value if hasattr(art.artifact_type, "value") else str(art.artifact_type),
                })
        units_data.append({
            "id": str(unit.id),
            "title": unit.title,
            "state": unit_state,
            "artifacts": artifacts_data,
        })

    return {
        "project_id": str(project_id),
        "project_title": project.title,
        "units": units_data,
    }
