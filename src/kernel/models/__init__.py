"""
Kernel Data Models

Core SQLAlchemy models for the Stable Kernel layer.
These models implement the artifact graph store with versioning.
"""

from src.kernel.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid
from src.kernel.models.user import User, UserRole, RefreshToken
from src.kernel.models.project import (
    ResearchProject,
    ProjectStatus,
    ProjectShare,
    DisciplineType,
    PermissionLevel,
)
from src.kernel.models.artifact import (
    Artifact,
    ArtifactType,
    ArtifactVersion,
    ArtifactLink,
    LinkType,
    Claim,
    ClaimType,
    Evidence,
    EvidenceType,
    Source,
    VerificationStatus,
    ProvenanceRecord,
    ContributionCategory,
    ArtifactState,
    compute_content_hash,
)
from src.kernel.models.submission_unit import SubmissionUnit, SubmissionUnitState
from src.kernel.models.collaboration import (
    CommentThread,
    Comment,
    ReviewRequest,
    ReviewStatus,
    ApprovalGate,
)
from src.kernel.models.review_response import ReviewResponse
from src.kernel.models.event_log import EventLog, EventType
from src.kernel.models.permission import Permission, PermissionLevel, ResourceType
from src.kernel.models.mastery import UserMasteryProgress, CheckpointAttempt
from src.kernel.models.avatar_conversation import AvatarMessage
from src.kernel.models.verification import ContentVerificationRequest

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid",
    # User
    "User",
    "UserRole",
    "RefreshToken",
    # Project
    "ResearchProject",
    "ProjectStatus",
    "ProjectShare",
    "DisciplineType",
    "PermissionLevel",
    # Artifacts
    "Artifact",
    "ArtifactType",
    "ArtifactVersion",
    "ArtifactLink",
    "LinkType",
    "Claim",
    "ClaimType",
    "Evidence",
    "EvidenceType",
    "Source",
    "VerificationStatus",
    "ProvenanceRecord",
    "ContributionCategory",
    "ArtifactState",
    "compute_content_hash",
    "SubmissionUnit",
    "SubmissionUnitState",
    # Collaboration
    "CommentThread",
    "Comment",
    "ReviewRequest",
    "ReviewStatus",
    "ApprovalGate",
    "ReviewResponse",
    # Event Log
    "EventLog",
    "EventType",
    # Permissions
    "Permission",
    "PermissionLevel",
    "ResourceType",
    # Mastery
    "UserMasteryProgress",
    "CheckpointAttempt",
    # Avatar
    "AvatarMessage",
    # Verification
    "ContentVerificationRequest",
]
