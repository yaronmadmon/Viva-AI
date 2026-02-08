"""
Validation endpoints - run batch validation for a project.
"""

import uuid
from typing import Dict

from fastapi import APIRouter, Query, status
from sqlalchemy import and_, select

from src.api.deps import CurrentUser, DbSession, RequireProjectView
from src.engines.validation.validation_service import ValidationService
from src.kernel.models.artifact import Artifact, ArtifactType, Source
from src.kernel.models.verification import ContentVerificationRequest as ContentVerificationRequestModel
from src.schemas.validation import ValidationRunResponse

router = APIRouter()


@router.post("/run", response_model=ValidationRunResponse)
async def run_project_validation(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
    run_api_checks: bool = Query(True, description="Call Crossref/OpenLibrary/arXiv APIs"),
):
    """
    Validate all sources in the project. Runs the full 5-layer verification per source.
    Any content checks (e.g. author/date mismatch) are persisted as verification requests
    and returned in created_verification_request_ids; use GET /verification/pending to list them.
    """
    # Build artifact_id -> Source.id for persisting verification requests
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
    r = await db.execute(q)
    rows = r.all()
    artifact_to_source_id: Dict[uuid.UUID, uuid.UUID] = {artifact.id: source.id for source, artifact in rows}

    service = ValidationService(db)
    results = await service.validate_all_sources_in_project(project_id=project_id, run_api_checks=run_api_checks)

    created_ids: list[uuid.UUID] = []
    for artifact_id, full in results.items():
        source_db_id = artifact_to_source_id.get(artifact_id)
        if not source_db_id or not full.content_checks_required:
            continue
        for check in full.content_checks_required:
            row = ContentVerificationRequestModel(
                source_id=source_db_id,
                claim_id=check.claim_id,
                check_type=check.check_type.value,
                prompt=check.prompt,
                context=check.context,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            created_ids.append(row.id)

    # Serialize results for response (FullValidationResult is Pydantic)
    results_dict = {str(aid): full.model_dump(mode="json") for aid, full in results.items()}
    overall_blocks = any(full.blocks_export for full in results.values())
    total = len(results)
    if total == 0:
        summary = "No sources to validate."
    elif overall_blocks:
        summary = f"Validated {total} source(s). Critical issues detected; export may be blocked."
    else:
        summary = f"Validated {total} source(s). No blocking issues."

    return ValidationRunResponse(
        project_id=project_id,
        total_sources=total,
        results=results_dict,
        created_verification_request_ids=created_ids,
        overall_blocks_export=overall_blocks,
        summary=summary,
    )
