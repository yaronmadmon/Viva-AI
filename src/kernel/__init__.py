"""
Stable Kernel Layer

This layer contains the foundational components that should NEVER be refactored:
- Artifact Graph Store (append-only with versioning)
- Immutable Event Log (all mutations logged)
- Identity Core (user accounts, roles)
- Permission Core (project-level, artifact-level ACLs)

Architectural Invariants (from design doc):
- All state changes logged before commit; logs immutable
- No direct database access from Plugin Layer
- Admin operations require separate audit trail
"""

from src.kernel.models import (
    User,
    UserRole,
    ResearchProject,
    ProjectStatus,
    Artifact,
    ArtifactType,
    ArtifactVersion,
    Claim,
    ClaimType,
    Evidence,
    EvidenceType,
    Source,
    VerificationStatus,
    ProvenanceRecord,
    EventLog,
    EventType,
    Permission,
    PermissionLevel,
    CommentThread,
    Comment,
    ProjectShare,
)

__all__ = [
    # User & Identity
    "User",
    "UserRole",
    # Project
    "ResearchProject",
    "ProjectStatus",
    # Artifacts
    "Artifact",
    "ArtifactType",
    "ArtifactVersion",
    # Claims & Evidence
    "Claim",
    "ClaimType",
    "Evidence",
    "EvidenceType",
    # Sources & Provenance
    "Source",
    "VerificationStatus",
    "ProvenanceRecord",
    # Event Log
    "EventLog",
    "EventType",
    # Permissions
    "Permission",
    "PermissionLevel",
    # Collaboration
    "CommentThread",
    "Comment",
    "ProjectShare",
]
