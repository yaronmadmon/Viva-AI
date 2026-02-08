"""
Project endpoints.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from src.api.deps import (
    DbSession,
    CurrentUser,
    RequireProjectView,
    RequireProjectEdit,
    get_client_ip,
)
from src.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectShareRequest,
    CollaboratorResponse,
    ProjectStatsResponse,
)
from src.schemas.common import SuccessResponse, PaginatedResponse
from src.kernel.models.project import ResearchProject, ProjectShare, ProjectStatus
from src.kernel.models.artifact import Artifact
from src.kernel.models.user import User
from src.kernel.models.event_log import EventType
from src.kernel.events.event_store import EventStore
from src.kernel.permissions.permission_service import PermissionService

router = APIRouter()


def _enum_val(e):
    """Safely get enum value (SQLite may return str)."""
    return e.value if hasattr(e, "value") else e


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    data: ProjectCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Create a new research project."""
    project = ResearchProject(
        title=data.title,
        description=data.description,
        discipline_type=data.discipline_type,
        owner_id=user.id,
        status=ProjectStatus.DRAFT,
    )
    
    db.add(project)
    await db.flush()
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_CREATED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={
            "title": project.title,
            "discipline_type": _enum_val(project.discipline_type),
        },
        ip_address=get_client_ip(request),
    )
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        discipline_type=_enum_val(project.discipline_type),
        status=_enum_val(project.status),
        owner_id=project.owner_id,
        owner_name=user.full_name,
        integrity_score=project.integrity_score,
        export_blocked=project.export_blocked,
        artifact_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=List[ProjectListResponse])
async def list_projects(
    user: CurrentUser,
    db: DbSession,
    include_shared: bool = Query(True, description="Include projects shared with you"),
    status_filter: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List user's projects (owned and shared)."""
    # Get owned projects
    query = select(ResearchProject, User).join(
        User, ResearchProject.owner_id == User.id
    ).where(
        and_(
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    
    if status_filter:
        query = query.where(ResearchProject.status == status_filter)
    
    result = await db.execute(query)
    owned_projects = result.all()
    
    projects = []
    for project, owner in owned_projects:
        # Count artifacts
        count_query = select(func.count(Artifact.id)).where(
            and_(
                Artifact.project_id == project.id,
                Artifact.deleted_at.is_(None),
            )
        )
        count_result = await db.execute(count_query)
        artifact_count = count_result.scalar() or 0
        
        projects.append(ProjectListResponse(
            id=project.id,
            title=project.title,
            description=project.description,
            discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
            owner_id=project.owner_id,
            owner_name=owner.full_name,
            integrity_score=project.integrity_score,
            is_owner=True,
            permission_level="owner",
            artifact_count=artifact_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        ))
    
    # Get shared projects
    if include_shared:
        shared_query = select(ResearchProject, User, ProjectShare).join(
            ProjectShare, ResearchProject.id == ProjectShare.project_id
        ).join(
            User, ResearchProject.owner_id == User.id
        ).where(
            and_(
                ProjectShare.user_id == user.id,
                ResearchProject.deleted_at.is_(None),
            )
        )
        
        if status_filter:
            shared_query = shared_query.where(ResearchProject.status == status_filter)
        
        shared_result = await db.execute(shared_query)
        
        for project, owner, share in shared_result.all():
            count_query = select(func.count(Artifact.id)).where(
                and_(
                    Artifact.project_id == project.id,
                    Artifact.deleted_at.is_(None),
                )
            )
            count_result = await db.execute(count_query)
            artifact_count = count_result.scalar() or 0
            
            projects.append(ProjectListResponse(
                id=project.id,
                title=project.title,
                description=project.description,
discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
                owner_id=project.owner_id,
                owner_name=owner.full_name,
                integrity_score=project.integrity_score,
                is_owner=False,
                permission_level=share.permission_level.value,
                artifact_count=artifact_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ))
    
    # Sort by updated_at descending
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    
    return projects[start:end]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get a project by ID."""
    query = select(ResearchProject, User).join(
        User, ResearchProject.owner_id == User.id
    ).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project, owner = row
    
    # Count artifacts
    count_query = select(func.count(Artifact.id)).where(
        and_(
            Artifact.project_id == project.id,
            Artifact.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_query)
    artifact_count = count_result.scalar() or 0
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
        owner_id=project.owner_id,
        owner_name=owner.full_name,
        integrity_score=project.integrity_score,
        export_blocked=project.export_blocked,
        artifact_count=artifact_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
):
    """Update a project."""
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
    
    # Update fields
    changes = {}
    if data.title is not None:
        changes["previous_title"] = project.title
        project.title = data.title
        changes["new_title"] = data.title
    
    if data.description is not None:
        project.description = data.description
    
    if data.discipline_type is not None:
        changes["previous_discipline"] = _enum_val(project.discipline_type)
        project.discipline_type = data.discipline_type
        changes["new_discipline"] = _enum_val(data.discipline_type)
    
    if data.status is not None:
        changes["previous_status"] = _enum_val(project.status)
        project.status = data.status
        changes["new_status"] = _enum_val(data.status)
    
    # Log the event
    if changes:
        event_store = EventStore(db)
        await event_store.log(
            event_type=EventType.PROJECT_UPDATED,
            entity_type="project",
            entity_id=project.id,
            user_id=user.id,
            payload=changes,
            ip_address=get_client_ip(request),
        )
    
    # Get owner name
    owner_query = select(User).where(User.id == project.owner_id)
    owner_result = await db.execute(owner_query)
    owner = owner_result.scalar_one()
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        discipline_type=_enum_val(project.discipline_type),
        status=_enum_val(project.status),
        owner_id=project.owner_id,
        owner_name=owner.full_name,
        integrity_score=project.integrity_score,
        export_blocked=project.export_blocked,
        artifact_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    request: Request,
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Delete a project (soft delete). Only owner can delete."""
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to delete it",
        )
    
    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_DELETED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={"title": project.title},
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Project deleted successfully")


@router.post("/{project_id}/share", response_model=CollaboratorResponse)
async def share_project(
    request: Request,
    project_id: uuid.UUID,
    data: ProjectShareRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Share a project with another user. Only owner can share."""
    # Verify ownership
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to share it",
        )
    
    # Find user to share with
    target_query = select(User).where(User.email == data.email.lower())
    target_result = await db.execute(target_query)
    target_user = target_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with that email",
        )
    
    if target_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share project with yourself",
        )
    
    # Check if already shared
    existing_query = select(ProjectShare).where(
        and_(
            ProjectShare.project_id == project_id,
            ProjectShare.user_id == target_user.id,
        )
    )
    existing_result = await db.execute(existing_query)
    existing_share = existing_result.scalar_one_or_none()
    
    if existing_share:
        # Update permission level
        existing_share.permission_level = data.permission_level
    else:
        # Create new share
        share = ProjectShare(
            project_id=project_id,
            user_id=target_user.id,
            permission_level=data.permission_level,
            invited_by=user.id,
        )
        db.add(share)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_SHARED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={
            "shared_with_user_id": str(target_user.id),
            "shared_with_email": target_user.email,
            "permission_level": data.permission_level.value,
        },
        ip_address=get_client_ip(request),
    )
    
    return CollaboratorResponse(
        user_id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=_enum_val(target_user.role),
        permission_level=data.permission_level.value,
        is_owner=False,
        accepted=True,
    )


@router.get("/{project_id}/collaborators", response_model=List[CollaboratorResponse])
async def list_collaborators(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """List all collaborators on a project."""
    permission_service = PermissionService(db)
    return await permission_service.get_project_collaborators(project_id)


@router.delete("/{project_id}/collaborators/{user_id}", response_model=SuccessResponse)
async def remove_collaborator(
    request: Request,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Remove a collaborator from a project. Only owner can remove."""
    # Verify ownership
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission",
        )
    
    # Find and remove share
    share_query = select(ProjectShare).where(
        and_(
            ProjectShare.project_id == project_id,
            ProjectShare.user_id == user_id,
        )
    )
    share_result = await db.execute(share_query)
    share = share_result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found",
        )
    
    await db.delete(share)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_UNSHARED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={"removed_user_id": str(user_id)},
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Collaborator removed successfully")
