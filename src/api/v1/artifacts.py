"""
Artifact endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from src.api.deps import (
    DbSession,
    CurrentUser,
    RequireProjectEdit,
    RequireProjectView,
    RequireArtifactEdit,
    get_client_ip,
)
from src.schemas.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactResponse,
    ArtifactDetailResponse,
    ArtifactLinkCreate,
    ArtifactLinkResponse,
    ArtifactVersionResponse,
    ArtifactTreeResponse,
    ArtifactTreeNode,
    ArtifactMoveRequest,
    ArtifactStateTransition,
)
from src.schemas.common import SuccessResponse
from src.kernel.models.artifact import (
    Artifact,
    ArtifactVersion,
    ArtifactLink,
    compute_content_hash,
    ContributionCategory,
)
from src.orchestration.state_machine import StateMachine, can_transition
from src.kernel.models.project import ResearchProject
from src.kernel.models.event_log import EventType
from src.kernel.events.event_store import EventStore
from src.kernel.permissions.permission_service import PermissionService
from src.kernel.models.permission import PermissionLevel
from src.engines.mastery.progress_tracker import ProgressTracker
from src.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _enum_val(e) -> str:
    """Safely get enum value (SQLite may return str)."""
    return e.value if hasattr(e, "value") else str(e)


def _word_count(text: str) -> int:
    """Count words in content for mastery tracking."""
    return len((text or "").split())


@router.post("/projects/{project_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: Request,
    project_id: uuid.UUID,
    data: ArtifactCreate,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
):
    """Create a new artifact in a project."""
    # Verify project exists
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # If parent_id provided, verify it exists and is in same project
    if data.parent_id:
        parent_query = select(Artifact).where(
            and_(
                Artifact.id == data.parent_id,
                Artifact.project_id == project_id,
                Artifact.deleted_at.is_(None),
            )
        )
        parent_result = await db.execute(parent_query)
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent artifact not found",
            )
    
    # Create artifact
    content_hash = compute_content_hash(data.content)
    
    artifact = Artifact(
        project_id=project_id,
        artifact_type=data.artifact_type,
        title=data.title,
        content=data.content,
        content_hash=content_hash,
        parent_id=data.parent_id,
        position=data.position,
        extra_data=data.metadata,
        contribution_category=ContributionCategory.PRIMARILY_HUMAN,
        ai_modification_ratio=1.0,
    )
    
    db.add(artifact)
    await db.flush()
    
    # Create initial version
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=1,
        title=artifact.title,
        content=artifact.content,
        content_hash=content_hash,
        created_by=user.id,
        contribution_category=ContributionCategory.PRIMARILY_HUMAN,
    )
    db.add(version)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.ARTIFACT_CREATED,
        entity_type="artifact",
        entity_id=artifact.id,
        user_id=user.id,
        payload={
            "project_id": str(project_id),
            "artifact_type": _enum_val(artifact.artifact_type),
            "title": artifact.title,
            "content_hash": content_hash,
        },
        ip_address=get_client_ip(request),
    )

    # Update mastery word count for this user/project
    words = _word_count(data.content)
    if words > 0:
        tracker = ProgressTracker(db)
        await tracker.update_word_count(user.id, project_id, words)

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=_enum_val(artifact.artifact_type),
        title=artifact.title,
        content=artifact.content,
        content_hash=artifact.content_hash,
        version=artifact.version,
        parent_id=artifact.parent_id,
        position=artifact.position,
        contribution_category=_enum_val(artifact.contribution_category),
        ai_modification_ratio=artifact.ai_modification_ratio,
        metadata=artifact.extra_data,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_artifact(
    artifact_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Get an artifact by ID with related data."""
    query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    ).options(
        selectinload(Artifact.children),
        selectinload(Artifact.outgoing_links),
        selectinload(Artifact.incoming_links),
    )
    
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.VIEW
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Build response
    children = [
        ArtifactResponse(
            id=c.id,
            project_id=c.project_id,
            artifact_type=_enum_val(c.artifact_type),
            title=c.title,
            content=c.content,
            content_hash=c.content_hash,
            version=c.version,
            parent_id=c.parent_id,
            position=c.position,
            contribution_category=_enum_val(c.contribution_category),
            ai_modification_ratio=c.ai_modification_ratio,
            metadata=c.extra_data,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in artifact.children if c.deleted_at is None
    ]
    
    outgoing_links = [
        ArtifactLinkResponse(
            id=l.id,
            source_artifact_id=l.source_artifact_id,
            target_artifact_id=l.target_artifact_id,
            link_type=_enum_val(l.link_type),
            strength=l.strength,
            annotation=l.annotation,
            created_by=l.created_by,
            created_at=l.created_at,
        )
        for l in artifact.outgoing_links
    ]
    
    incoming_links = [
        ArtifactLinkResponse(
            id=l.id,
            source_artifact_id=l.source_artifact_id,
            target_artifact_id=l.target_artifact_id,
            link_type=_enum_val(l.link_type),
            strength=l.strength,
            annotation=l.annotation,
            created_by=l.created_by,
            created_at=l.created_at,
        )
        for l in artifact.incoming_links
    ]
    
    return ArtifactDetailResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=_enum_val(artifact.artifact_type),
        title=artifact.title,
        content=artifact.content,
        content_hash=artifact.content_hash,
        version=artifact.version,
        parent_id=artifact.parent_id,
        position=artifact.position,
        contribution_category=_enum_val(artifact.contribution_category),
        ai_modification_ratio=artifact.ai_modification_ratio,
        metadata=artifact.extra_data,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        children_count=len(children),
        outgoing_links_count=len(outgoing_links),
        incoming_links_count=len(incoming_links),
        children=children,
        outgoing_links=outgoing_links,
        incoming_links=incoming_links,
    )


@router.patch("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    request: Request,
    artifact_id: uuid.UUID,
    data: ArtifactUpdate,
    user: CurrentUser,
    db: DbSession,
):
    """Update an artifact. Creates a new version."""
    query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.EDIT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission required",
        )
    
    previous_hash = artifact.content_hash
    previous_content = artifact.content

    # Update fields
    if data.title is not None:
        artifact.title = data.title

    if data.content is not None:
        artifact.content = data.content
        artifact.content_hash = compute_content_hash(data.content)
    
    if data.position is not None:
        artifact.position = data.position
    
    if data.metadata is not None:
        artifact.extra_data = data.metadata
    
    # Increment version
    artifact.version += 1
    
    # Create version record
    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=artifact.version,
        title=artifact.title,
        content=artifact.content,
        content_hash=artifact.content_hash,
        created_by=user.id,
        contribution_category=artifact.contribution_category,
    )
    db.add(version)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.ARTIFACT_UPDATED,
        entity_type="artifact",
        entity_id=artifact.id,
        user_id=user.id,
        payload={
            "project_id": str(artifact.project_id),
            "previous_content_hash": previous_hash,
            "new_content_hash": artifact.content_hash,
            "version_number": artifact.version,
        },
        ip_address=get_client_ip(request),
    )

    # Update mastery word count when content changed
    if data.content is not None:
        words_old = _word_count(previous_content)
        words_new = _word_count(data.content)
        delta = max(0, words_new - words_old)
        if delta > 0:
            tracker = ProgressTracker(db)
            await tracker.update_word_count(user.id, artifact.project_id, delta)

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=_enum_val(artifact.artifact_type),
        title=artifact.title,
        content=artifact.content,
        content_hash=artifact.content_hash,
        version=artifact.version,
        parent_id=artifact.parent_id,
        position=artifact.position,
        contribution_category=_enum_val(artifact.contribution_category),
        ai_modification_ratio=artifact.ai_modification_ratio,
        metadata=artifact.extra_data,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.patch("/{artifact_id}/state", response_model=ArtifactResponse)
async def transition_artifact_state(
    request: Request,
    artifact_id: uuid.UUID,
    data: ArtifactStateTransition,
    user: CurrentUser,
    db: DbSession,
):
    """Transition artifact state (for artifacts not in a submission unit)."""
    query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.submission_unit_id:
        raise HTTPException(
            status_code=400,
            detail="Artifact is in a submission unit; transition unit state instead",
        )

    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.EDIT
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="Edit permission required")

    if not can_transition(user.role, _enum_val(artifact.internal_state), data.to_state, "artifact"):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot transition from {_enum_val(artifact.internal_state)} to {data.to_state}",
        )

    sm = StateMachine(db)
    await sm.transition_artifact(
        artifact=artifact,
        to_state=data.to_state,
        user_id=user.id,
        user_role=user.role,
        ip_address=get_client_ip(request),
    )
    await db.flush()
    await db.refresh(artifact)
    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=_enum_val(artifact.artifact_type),
        title=artifact.title,
        content=artifact.content,
        content_hash=artifact.content_hash,
        version=artifact.version,
        parent_id=artifact.parent_id,
        position=artifact.position,
        contribution_category=_enum_val(artifact.contribution_category),
        ai_modification_ratio=artifact.ai_modification_ratio,
        metadata=artifact.extra_data,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.delete("/{artifact_id}", response_model=SuccessResponse)
async def delete_artifact(
    request: Request,
    artifact_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Delete an artifact (soft delete)."""
    query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.EDIT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission required",
        )
    
    artifact.deleted_at = datetime.now(timezone.utc)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.ARTIFACT_DELETED,
        entity_type="artifact",
        entity_id=artifact.id,
        user_id=user.id,
        payload={
            "project_id": str(artifact.project_id),
            "artifact_type": _enum_val(artifact.artifact_type),
        },
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Artifact deleted successfully")


@router.post("/{artifact_id}/link", response_model=ArtifactLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    request: Request,
    artifact_id: uuid.UUID,
    data: ArtifactLinkCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Create a link between two artifacts."""
    # Get source artifact
    source_query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    source_result = await db.execute(source_query)
    source = source_result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source artifact not found",
        )
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, source.project_id, PermissionLevel.EDIT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edit permission required",
        )
    
    # Get target artifact
    target_query = select(Artifact).where(
        and_(
            Artifact.id == data.target_artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    target_result = await db.execute(target_query)
    target = target_result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target artifact not found",
        )
    
    # Create link
    link = ArtifactLink(
        source_artifact_id=artifact_id,
        target_artifact_id=data.target_artifact_id,
        link_type=data.link_type,
        strength=data.strength,
        annotation=data.annotation,
        created_by=user.id,
    )
    
    db.add(link)
    await db.flush()
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.ARTIFACT_LINKED,
        entity_type="artifact_link",
        entity_id=link.id,
        user_id=user.id,
        payload={
            "source_artifact_id": str(artifact_id),
            "target_artifact_id": str(data.target_artifact_id),
            "link_type": _enum_val(data.link_type),
        },
        ip_address=get_client_ip(request),
    )
    
    return ArtifactLinkResponse(
        id=link.id,
        source_artifact_id=link.source_artifact_id,
        target_artifact_id=link.target_artifact_id,
        link_type=_enum_val(link.link_type),
        strength=link.strength,
        annotation=link.annotation,
        created_by=link.created_by,
        created_at=link.created_at,
        source_title=source.title,
        source_type=_enum_val(source.artifact_type),
        target_title=target.title,
        target_type=_enum_val(target.artifact_type),
    )


@router.get("/{artifact_id}/history", response_model=List[ArtifactVersionResponse])
async def get_artifact_history(
    artifact_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
):
    """Get version history for an artifact."""
    # Get artifact
    artifact_query = select(Artifact).where(Artifact.id == artifact_id)
    artifact_result = await db.execute(artifact_query)
    artifact = artifact_result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.VIEW
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get versions
    query = select(ArtifactVersion).where(
        ArtifactVersion.artifact_id == artifact_id
    ).order_by(ArtifactVersion.version_number.desc()).limit(limit)
    
    result = await db.execute(query)
    versions = result.scalars().all()
    
    return [
        ArtifactVersionResponse(
            id=v.id,
            artifact_id=v.artifact_id,
            version_number=v.version_number,
            title=v.title,
            content=v.content,
            content_hash=v.content_hash,
            contribution_category=_enum_val(v.contribution_category),
            created_by=v.created_by,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get("/projects/{project_id}/tree", response_model=ArtifactTreeResponse)
async def get_artifact_tree(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get the full artifact tree for a project."""
    try:
        # Get all artifacts for the project
        query = select(Artifact).where(
            and_(
                Artifact.project_id == project_id,
                Artifact.deleted_at.is_(None),
            )
        ).order_by(Artifact.position)

        result = await db.execute(query)
        artifacts = result.scalars().all()

        # Build tree structure
        artifact_map = {a.id: a for a in artifacts}
        root_artifacts = []

        def build_node(artifact: Artifact) -> ArtifactTreeNode:
            children = []
            for child in artifacts:
                if child.parent_id != artifact.id:
                    continue
                if child.id not in artifact_map:
                    continue
                try:
                    children.append(build_node(artifact_map[child.id]))
                except Exception as e:
                    logger.warning("Skipping artifact %s in tree: %s", child.id, e)
            return ArtifactTreeNode(
                id=artifact.id,
                artifact_type=_enum_val(artifact.artifact_type),
                title=artifact.title,
                position=artifact.position,
                version=artifact.version,
                children=sorted(children, key=lambda c: c.position),
            )

        for artifact in artifacts:
            if artifact.parent_id is None:
                root_artifacts.append(build_node(artifact))

        return ArtifactTreeResponse(
            project_id=project_id,
            root_artifacts=sorted(root_artifacts, key=lambda a: a.position),
            total_count=len(artifacts),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Artifact tree error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build artifact tree",
        ) from e
