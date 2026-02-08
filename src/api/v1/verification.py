"""
Content verification endpoints - manual verification workflow.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from src.api.deps import CurrentUser, DbSession
from src.kernel.models.artifact import Artifact, Source
from src.kernel.models.permission import PermissionLevel
from src.kernel.models.verification import ContentVerificationRequest as ContentVerificationRequestModel
from src.kernel.permissions.permission_service import PermissionService
from src.schemas.verification import (
    ContentVerificationRequestCreate,
    ContentVerificationRequestResponse,
    VerifyResponseBody,
)

router = APIRouter()


def _to_response(row: ContentVerificationRequestModel) -> ContentVerificationRequestResponse:
    return ContentVerificationRequestResponse(
        id=row.id,
        source_id=row.source_id,
        claim_id=row.claim_id,
        check_type=row.check_type,
        prompt=row.prompt,
        context=row.context,
        resolved=row.resolved_at is not None,
        verified=row.verified,
        notes=row.notes,
        verified_at=row.verified_at,
        created_at=row.created_at,
    )


@router.get("/pending", response_model=List[ContentVerificationRequestResponse])
async def list_pending_verification_requests(
    user: CurrentUser,
    db: DbSession,
    project_id: uuid.UUID = Query(..., description="Project to list pending requests for"),
):
    """List unresolved content verification requests for a project."""
    permission_service = PermissionService(db)
    has = await permission_service.check_project_permission(user, project_id, PermissionLevel.VIEW)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Source IDs that belong to artifacts in this project
    artifact_ids = select(Artifact.id).where(
        Artifact.project_id == project_id,
        Artifact.deleted_at.is_(None),
    )
    source_ids = select(Source.id).where(Source.artifact_id.in_(artifact_ids))
    q = (
        select(ContentVerificationRequestModel)
        .where(ContentVerificationRequestModel.source_id.in_(source_ids))
        .where(ContentVerificationRequestModel.resolved_at.is_(None))
    )
    result = await db.execute(q)
    rows = result.scalars().all()
    return [_to_response(r) for r in rows]


@router.post("/requests", response_model=ContentVerificationRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_verification_request(
    user: CurrentUser,
    db: DbSession,
    data: ContentVerificationRequestCreate,
):
    """Create a content verification request (e.g. from validation flow)."""
    # Verify source exists and user has access to its project
    q = select(Source, Artifact).join(Artifact, Source.artifact_id == Artifact.id).where(Source.id == data.source_id)
    r = await db.execute(q)
    row_pair = r.one_or_none()
    if not row_pair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    source, art = row_pair
    permission_service = PermissionService(db)
    has = await permission_service.check_project_permission(user, art.project_id, PermissionLevel.EDIT)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    row = ContentVerificationRequestModel(
        source_id=data.source_id,
        claim_id=data.claim_id,
        check_type=data.check_type,
        prompt=data.prompt,
        context=data.context,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return _to_response(row)


@router.post("/requests/{request_id}/respond", response_model=ContentVerificationRequestResponse)
async def respond_to_verification_request(
    user: CurrentUser,
    db: DbSession,
    request_id: uuid.UUID,
    body: VerifyResponseBody,
):
    """Submit a response to a content verification request."""
    q = select(ContentVerificationRequestModel).where(ContentVerificationRequestModel.id == request_id)
    result = await db.execute(q)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")
    if row.resolved_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already resolved")

    # Check access via source -> artifact -> project
    art_q = select(Artifact).join(Source, Source.artifact_id == Artifact.id).where(Source.id == row.source_id)
    art_r = await db.execute(art_q)
    art = art_r.scalar_one_or_none()
    if not art:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source or artifact not found")
    permission_service = PermissionService(db)
    has = await permission_service.check_project_permission(user, art.project_id, PermissionLevel.EDIT)
    if not has:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    now = datetime.now(timezone.utc)
    row.resolved_at = now
    row.verified_at = now
    row.verified_by = user.id
    row.verified = body.verified
    row.notes = body.notes
    await db.flush()
    await db.refresh(row)
    return _to_response(row)
