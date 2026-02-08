"""
Collaboration endpoints - comments, reviews, and threads.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select, and_, func

from src.api.deps import (
    DbSession,
    CurrentUser,
    get_client_ip,
)
from src.schemas.collaboration import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentThreadCreate,
    CommentThreadResponse,
    ThreadResolveRequest,
    ReviewRequestCreate,
    ReviewRequestResponse,
    ReviewResponseRequest,
)
from src.schemas.common import SuccessResponse
from src.kernel.models.collaboration import CommentThread, Comment, ReviewRequest, ReviewStatus
from src.kernel.models.user import UserRole
from src.kernel.models.artifact import Artifact
from src.kernel.models.project import ResearchProject
from src.kernel.models.user import User
from src.kernel.models.event_log import EventType
from src.kernel.events.event_store import EventStore
from src.kernel.permissions.permission_service import PermissionService
from src.kernel.models.permission import PermissionLevel

router = APIRouter()


# Comment Thread endpoints

@router.post("/artifacts/{artifact_id}/threads", response_model=CommentThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_comment_thread(
    request: Request,
    artifact_id: uuid.UUID,
    data: CommentThreadCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Create a new comment thread on an artifact with initial comment."""
    # Get artifact
    artifact_query = select(Artifact).where(
        and_(
            Artifact.id == artifact_id,
            Artifact.deleted_at.is_(None),
        )
    )
    artifact_result = await db.execute(artifact_query)
    artifact = artifact_result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    # Check permission (need at least comment permission)
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.COMMENT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comment permission required",
        )
    
    # Create thread
    thread = CommentThread(
        artifact_id=artifact_id,
        resolved=False,
    )
    db.add(thread)
    await db.flush()
    
    # Create initial comment
    comment = Comment(
        thread_id=thread.id,
        author_id=user.id,
        content=data.content,
    )
    db.add(comment)
    await db.flush()
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.COMMENT_ADDED,
        entity_type="comment",
        entity_id=comment.id,
        user_id=user.id,
        payload={
            "thread_id": str(thread.id),
            "artifact_id": str(artifact_id),
            "content_preview": data.content[:100],
        },
        ip_address=get_client_ip(request),
    )
    
    return CommentThreadResponse(
        id=thread.id,
        artifact_id=thread.artifact_id,
        resolved=thread.resolved,
        resolved_at=thread.resolved_at,
        resolved_by=thread.resolved_by,
        comment_count=1,
        comments=[
            CommentResponse(
                id=comment.id,
                thread_id=comment.thread_id,
                author_id=comment.author_id,
                author_name=user.full_name,
                author_email=user.email,
                content=comment.content,
                edited_at=comment.edited_at,
                created_at=comment.created_at,
            )
        ],
        created_at=thread.created_at,
    )


@router.get("/artifacts/{artifact_id}/threads", response_model=List[CommentThreadResponse])
async def list_comment_threads(
    artifact_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    include_resolved: bool = Query(True, description="Include resolved threads"),
):
    """List all comment threads on an artifact."""
    # Get artifact and check permission
    artifact_query = select(Artifact).where(Artifact.id == artifact_id)
    artifact_result = await db.execute(artifact_query)
    artifact = artifact_result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.VIEW
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get threads
    query = select(CommentThread).where(CommentThread.artifact_id == artifact_id)
    if not include_resolved:
        query = query.where(CommentThread.resolved == False)
    query = query.order_by(CommentThread.created_at.desc())
    
    result = await db.execute(query)
    threads = result.scalars().all()
    
    # Build response with comments
    response = []
    for thread in threads:
        # Get comments for this thread
        comments_query = select(Comment, User).join(
            User, Comment.author_id == User.id
        ).where(
            Comment.thread_id == thread.id
        ).order_by(Comment.created_at)
        
        comments_result = await db.execute(comments_query)
        comments = [
            CommentResponse(
                id=c.id,
                thread_id=c.thread_id,
                author_id=c.author_id,
                author_name=u.full_name,
                author_email=u.email,
                content=c.content,
                edited_at=c.edited_at,
                created_at=c.created_at,
            )
            for c, u in comments_result.all()
        ]
        
        response.append(CommentThreadResponse(
            id=thread.id,
            artifact_id=thread.artifact_id,
            resolved=thread.resolved,
            resolved_at=thread.resolved_at,
            resolved_by=thread.resolved_by,
            comment_count=len(comments),
            comments=comments,
            created_at=thread.created_at,
        ))
    
    return response


@router.post("/threads/{thread_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment_to_thread(
    request: Request,
    thread_id: uuid.UUID,
    data: CommentCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Add a comment to an existing thread."""
    # Get thread with artifact
    thread_query = select(CommentThread, Artifact).join(
        Artifact, CommentThread.artifact_id == Artifact.id
    ).where(CommentThread.id == thread_id)
    
    thread_result = await db.execute(thread_query)
    row = thread_result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    
    thread, artifact = row
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.COMMENT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comment permission required",
        )
    
    # Create comment
    comment = Comment(
        thread_id=thread_id,
        author_id=user.id,
        content=data.content,
    )
    db.add(comment)
    await db.flush()
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.COMMENT_ADDED,
        entity_type="comment",
        entity_id=comment.id,
        user_id=user.id,
        payload={
            "thread_id": str(thread_id),
            "artifact_id": str(artifact.id),
        },
        ip_address=get_client_ip(request),
    )
    
    return CommentResponse(
        id=comment.id,
        thread_id=comment.thread_id,
        author_id=comment.author_id,
        author_name=user.full_name,
        author_email=user.email,
        content=comment.content,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
    )


@router.patch("/threads/{thread_id}/resolve", response_model=CommentThreadResponse)
async def resolve_thread(
    request: Request,
    thread_id: uuid.UUID,
    data: ThreadResolveRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Resolve or unresolve a comment thread."""
    # Get thread
    thread_query = select(CommentThread, Artifact).join(
        Artifact, CommentThread.artifact_id == Artifact.id
    ).where(CommentThread.id == thread_id)
    
    thread_result = await db.execute(thread_query)
    row = thread_result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    
    thread, artifact = row
    
    # Check permission
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, artifact.project_id, PermissionLevel.COMMENT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
    
    # Update thread
    thread.resolved = data.resolved
    if data.resolved:
        thread.resolved_at = datetime.now(timezone.utc)
        thread.resolved_by = user.id
    else:
        thread.resolved_at = None
        thread.resolved_by = None
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.THREAD_RESOLVED if data.resolved else EventType.THREAD_REOPENED,
        entity_type="comment_thread",
        entity_id=thread.id,
        user_id=user.id,
        payload={"resolved": data.resolved},
        ip_address=get_client_ip(request),
    )
    
    # Get comments
    comments_query = select(Comment, User).join(
        User, Comment.author_id == User.id
    ).where(Comment.thread_id == thread.id).order_by(Comment.created_at)
    
    comments_result = await db.execute(comments_query)
    comments = [
        CommentResponse(
            id=c.id,
            thread_id=c.thread_id,
            author_id=c.author_id,
            author_name=u.full_name,
            content=c.content,
            edited_at=c.edited_at,
            created_at=c.created_at,
        )
        for c, u in comments_result.all()
    ]
    
    return CommentThreadResponse(
        id=thread.id,
        artifact_id=thread.artifact_id,
        resolved=thread.resolved,
        resolved_at=thread.resolved_at,
        resolved_by=thread.resolved_by,
        comment_count=len(comments),
        comments=comments,
        created_at=thread.created_at,
    )


# Review Request endpoints

@router.post("/projects/{project_id}/reviews", response_model=ReviewRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_review(
    request: Request,
    project_id: uuid.UUID,
    data: ReviewRequestCreate,
    user: CurrentUser,
    db: DbSession,
):
    """Request a review from an advisor."""
    # Check project exists and user has access
    project_query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, project_id, PermissionLevel.EDIT
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )
    
    # Find reviewer by email
    reviewer_query = select(User).where(User.email == data.reviewer_email.lower())
    reviewer_result = await db.execute(reviewer_query)
    reviewer = reviewer_result.scalar_one_or_none()
    
    if not reviewer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reviewer not found",
        )
    
    # Create review request
    review = ReviewRequest(
        project_id=project_id,
        artifact_id=data.artifact_id,
        requested_by=user.id,
        reviewer_id=reviewer.id,
        status=ReviewStatus.PENDING,
        message=data.message,
    )
    db.add(review)
    await db.flush()
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.REVIEW_REQUESTED,
        entity_type="review_request",
        entity_id=review.id,
        user_id=user.id,
        payload={
            "project_id": str(project_id),
            "reviewer_id": str(reviewer.id),
        },
        ip_address=get_client_ip(request),
    )
    
    return ReviewRequestResponse(
        id=review.id,
        project_id=review.project_id,
        artifact_id=review.artifact_id,
        requested_by=review.requested_by,
        requester_name=user.full_name,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.full_name,
        status=review.status.value,
        message=review.message,
        response_message=review.response_message,
        responded_at=review.responded_at,
        created_at=review.created_at,
    )


@router.get("/advisors/reviews", response_model=List[ReviewRequestResponse])
async def list_advisor_review_queue(
    user: CurrentUser,
    db: DbSession,
    status_filter: ReviewStatus = Query(None, description="Filter by status"),
):
    """List reviews assigned to current advisor (advisor queue)."""
    if user.role != UserRole.ADVISOR and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Advisor role required",
        )
    query = select(ReviewRequest).where(ReviewRequest.reviewer_id == user.id)
    if status_filter:
        query = query.where(ReviewRequest.status == status_filter)
    query = query.order_by(ReviewRequest.created_at.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()
    response = []
    for review in reviews:
        requester_query = select(User).where(User.id == review.requested_by)
        requester_result = await db.execute(requester_query)
        requester = requester_result.scalar_one_or_none() or user
        reviewer_query = select(User).where(User.id == review.reviewer_id)
        reviewer_result = await db.execute(reviewer_query)
        reviewer = reviewer_result.scalar_one_or_none() or user
        status_val = review.status.value if hasattr(review.status, "value") else str(review.status)
        response.append(ReviewRequestResponse(
            id=review.id,
            project_id=review.project_id,
            artifact_id=review.artifact_id,
            requested_by=review.requested_by,
            requester_name=requester.full_name,
            reviewer_id=review.reviewer_id,
            reviewer_name=reviewer.full_name,
            status=status_val,
            message=review.message,
            response_message=review.response_message,
            responded_at=review.responded_at,
            created_at=review.created_at,
        ))
    return response


@router.get("/projects/{project_id}/reviews", response_model=List[ReviewRequestResponse])
async def list_reviews(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    status_filter: ReviewStatus = Query(None, description="Filter by status"),
):
    """List review requests for a project."""
    permission_service = PermissionService(db)
    has_permission = await permission_service.check_project_permission(
        user, project_id, PermissionLevel.VIEW
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    query = select(ReviewRequest).where(ReviewRequest.project_id == project_id)
    if status_filter:
        query = query.where(ReviewRequest.status == status_filter)
    query = query.order_by(ReviewRequest.created_at.desc())
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    # Get user names
    response = []
    for review in reviews:
        requester_query = select(User).where(User.id == review.requested_by)
        requester = (await db.execute(requester_query)).scalar_one()
        
        reviewer_query = select(User).where(User.id == review.reviewer_id)
        reviewer = (await db.execute(reviewer_query)).scalar_one()
        
        status_val = review.status.value if hasattr(review.status, "value") else str(review.status)
        response.append(ReviewRequestResponse(
            id=review.id,
            project_id=review.project_id,
            artifact_id=review.artifact_id,
            requested_by=review.requested_by,
            requester_name=requester.full_name,
            reviewer_id=review.reviewer_id,
            reviewer_name=reviewer.full_name,
            status=status_val,
            message=review.message,
            response_message=review.response_message,
            responded_at=review.responded_at,
            created_at=review.created_at,
        ))
    
    return response


@router.patch("/reviews/{review_id}/respond", response_model=ReviewRequestResponse)
async def respond_to_review(
    request: Request,
    review_id: uuid.UUID,
    data: ReviewResponseRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Respond to a review request (advisor only)."""
    query = select(ReviewRequest).where(ReviewRequest.id == review_id)
    result = await db.execute(query)
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review request not found",
        )
    
    # Only the assigned reviewer can respond
    if review.reviewer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned reviewer can respond",
        )
    
    # Update review
    review.status = data.status
    review.response_message = data.response_message
    review.responded_at = datetime.now(timezone.utc)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.REVIEW_RESPONDED,
        entity_type="review_request",
        entity_id=review.id,
        user_id=user.id,
        payload={
            "status": data.status.value,
        },
        ip_address=get_client_ip(request),
    )
    
    # Get names
    requester_query = select(User).where(User.id == review.requested_by)
    requester = (await db.execute(requester_query)).scalar_one()
    
    return ReviewRequestResponse(
        id=review.id,
        project_id=review.project_id,
        artifact_id=review.artifact_id,
        requested_by=review.requested_by,
        requester_name=requester.full_name,
        reviewer_id=review.reviewer_id,
        reviewer_name=user.full_name,
        status=review.status.value,
        message=review.message,
        response_message=review.response_message,
        responded_at=review.responded_at,
        created_at=review.created_at,
    )
