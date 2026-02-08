"""
Pydantic schemas for API request/response validation.
"""

from src.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from src.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectShareRequest,
    CollaboratorResponse,
)
from src.schemas.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactResponse,
    ArtifactLinkCreate,
    ArtifactLinkResponse,
    ArtifactVersionResponse,
    ArtifactTreeResponse,
)
from src.schemas.collaboration import (
    CommentCreate,
    CommentResponse,
    CommentThreadResponse,
    ReviewRequestCreate,
    ReviewResponseRequest,
)
from src.schemas.common import (
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    # Auth
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectShareRequest",
    "CollaboratorResponse",
    # Artifact
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactResponse",
    "ArtifactLinkCreate",
    "ArtifactLinkResponse",
    "ArtifactVersionResponse",
    "ArtifactTreeResponse",
    # Collaboration
    "CommentCreate",
    "CommentResponse",
    "CommentThreadResponse",
    "ReviewRequestCreate",
    "ReviewResponseRequest",
    # Common
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
]
