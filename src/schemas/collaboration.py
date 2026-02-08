"""
Collaboration schemas.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.kernel.models.collaboration import ReviewStatus


class CommentCreate(BaseModel):
    """Comment creation request."""
    
    content: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    """Comment update request."""
    
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    """Comment response."""
    
    id: uuid.UUID
    thread_id: uuid.UUID
    author_id: uuid.UUID
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    content: str
    edited_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentThreadCreate(BaseModel):
    """Comment thread creation request (with first comment)."""
    
    content: str = Field(..., min_length=1, max_length=5000)


class CommentThreadResponse(BaseModel):
    """Comment thread response."""
    
    id: uuid.UUID
    artifact_id: uuid.UUID
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[uuid.UUID]
    comment_count: int = 0
    comments: List[CommentResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class ThreadResolveRequest(BaseModel):
    """Request to resolve/unresolve a thread."""
    
    resolved: bool


class ReviewRequestCreate(BaseModel):
    """Review request creation."""
    
    reviewer_email: str  # Email of the advisor to request review from
    artifact_id: Optional[uuid.UUID] = None  # If None, review entire project
    message: Optional[str] = Field(None, max_length=2000)


class ReviewRequestResponse(BaseModel):
    """Review request response."""
    
    id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: Optional[uuid.UUID]
    requested_by: uuid.UUID
    requester_name: Optional[str] = None
    reviewer_id: uuid.UUID
    reviewer_name: Optional[str] = None
    status: str
    message: Optional[str]
    response_message: Optional[str]
    responded_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReviewResponseRequest(BaseModel):
    """Review response request."""
    
    status: ReviewStatus
    response_message: Optional[str] = Field(None, max_length=2000)


class NotificationResponse(BaseModel):
    """Notification response."""
    
    id: uuid.UUID
    notification_type: str
    title: str
    message: str
    link: Optional[str]
    read: bool
    created_at: datetime
