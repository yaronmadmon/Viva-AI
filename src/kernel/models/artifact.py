"""
Artifact models - the core research objects.

Implements the artifact graph with adjacency list pattern for PostgreSQL.
"""

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    Index,
    JSON,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.kernel.models.base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid

if TYPE_CHECKING:
    from src.kernel.models.project import ResearchProject
    from src.kernel.models.collaboration import CommentThread


class ArtifactType(str, Enum):
    """Types of artifacts in the research graph."""
    SECTION = "section"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    SOURCE = "source"
    NOTE = "note"
    METHOD = "method"
    RESULT = "result"
    DISCUSSION = "discussion"


class ClaimType(str, Enum):
    """Types of claims."""
    HYPOTHESIS = "hypothesis"
    ARGUMENT = "argument"
    FINDING = "finding"
    INTERPRETATION = "interpretation"


class EvidenceType(str, Enum):
    """Types of evidence."""
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    MIXED = "mixed"
    CITATION = "citation"


class VerificationStatus(str, Enum):
    """Source verification status."""
    UNVERIFIED = "unverified"
    FORMAT_VALID = "format_valid"
    EXISTS_VERIFIED = "exists_verified"
    CONTENT_VERIFIED = "content_verified"
    FLAGGED = "flagged"


class LinkType(str, Enum):
    """Types of links between artifacts."""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CITES = "cites"
    CONTAINS = "contains"
    EXTENDS = "extends"
    QUALIFIES = "qualifies"


class ArtifactState(str, Enum):
    """Internal state of an artifact (student workflow). When in a unit, effective state = unit state."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    REVISIONS_REQUIRED = "revisions_required"
    APPROVED = "approved"
    LOCKED = "locked"
    ARCHIVED = "archived"


class ContributionCategory(str, Enum):
    """AI contribution categories for integrity scoring."""
    PRIMARILY_HUMAN = "primarily_human"      # >70% modification
    HUMAN_GUIDED = "human_guided"            # 30-70% modification
    AI_REVIEWED = "ai_reviewed"              # <30% modification (warning)
    UNMODIFIED_AI = "unmodified_ai"          # Verbatim (blocks export)


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


class Artifact(Base, TimestampMixin, SoftDeleteMixin):
    """
    Core artifact model - represents any scholarly work unit.
    
    Uses adjacency list pattern for parent-child relationships.
    """
    
    __tablename__ = "artifacts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Type and hierarchy
    artifact_type: Mapped[ArtifactType] = mapped_column(
        String(50),
        nullable=False,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    # Content
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    
    # Versioning
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    
    # Submission unit (optional) - when set, effective state = unit state
    submission_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("submission_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Internal state (student workflow); effective state = unit state when in unit
    internal_state: Mapped[ArtifactState] = mapped_column(
        String(50),
        default=ArtifactState.DRAFT,
        nullable=False,
    )

    # AI tracking
    contribution_category: Mapped[ContributionCategory] = mapped_column(
        String(50),
        default=ContributionCategory.PRIMARILY_HUMAN,
        nullable=False,
    )
    ai_modification_ratio: Mapped[float] = mapped_column(
        Float,
        default=1.0,  # 1.0 = 100% human
        nullable=False,
    )
    
    # Extra data (metadata is reserved by SQLAlchemy)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Relationships
    project: Mapped["ResearchProject"] = relationship(
        "ResearchProject",
        back_populates="artifacts",
    )
    parent: Mapped[Optional["Artifact"]] = relationship(
        "Artifact",
        remote_side="Artifact.id",
        back_populates="children",
    )
    children: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    versions: Mapped[List["ArtifactVersion"]] = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ArtifactVersion.version_number.desc()",
    )
    outgoing_links: Mapped[List["ArtifactLink"]] = relationship(
        "ArtifactLink",
        foreign_keys="ArtifactLink.source_artifact_id",
        back_populates="source_artifact",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[List["ArtifactLink"]] = relationship(
        "ArtifactLink",
        foreign_keys="ArtifactLink.target_artifact_id",
        back_populates="target_artifact",
        cascade="all, delete-orphan",
    )
    comment_threads: Mapped[List["CommentThread"]] = relationship(
        "CommentThread",
        back_populates="artifact",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_artifacts_project_parent", "project_id", "parent_id"),
        Index("ix_artifacts_project_type", "project_id", "artifact_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Artifact {self.artifact_type.value} {self.id}>"


class ArtifactVersion(Base):
    """Immutable version history for artifacts."""
    
    __tablename__ = "artifact_versions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    # Content snapshot
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    
    # Attribution
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # AI tracking for this version
    contribution_category: Mapped[ContributionCategory] = mapped_column(
        String(50),
        default=ContributionCategory.PRIMARILY_HUMAN,
        nullable=False,
    )
    
    # Relationships
    artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        back_populates="versions",
    )
    
    __table_args__ = (
        Index("ix_artifact_versions_artifact_version", "artifact_id", "version_number", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<ArtifactVersion {self.artifact_id} v{self.version_number}>"


class ArtifactLink(Base, TimestampMixin):
    """Links between artifacts in the research graph."""
    
    __tablename__ = "artifact_links"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_type: Mapped[LinkType] = mapped_column(
        String(50),
        nullable=False,
    )
    strength: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    # Optional annotation
    annotation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Relationships
    source_artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        foreign_keys=[source_artifact_id],
        back_populates="outgoing_links",
    )
    target_artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        foreign_keys=[target_artifact_id],
        back_populates="incoming_links",
    )
    
    __table_args__ = (
        Index("ix_artifact_links_source_target", "source_artifact_id", "target_artifact_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ArtifactLink {self.source_artifact_id} -{self.link_type.value}-> {self.target_artifact_id}>"


# Specialized artifact types with additional fields

class Claim(Base, TimestampMixin):
    """Extended claim data linked to an artifact."""
    
    __tablename__ = "claims"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    claim_type: Mapped[ClaimType] = mapped_column(
        String(50),
        nullable=False,
    )
    confidence_level: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
    )
    requires_evidence: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )


class Evidence(Base, TimestampMixin):
    """Extended evidence data linked to an artifact."""
    
    __tablename__ = "evidence"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    evidence_type: Mapped[EvidenceType] = mapped_column(
        String(50),
        nullable=False,
    )
    strength_rating: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        nullable=False,
    )
    source_refs: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )


class Source(Base, TimestampMixin):
    """External source/citation linked to an artifact."""
    
    __tablename__ = "sources"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    # Citation data
    citation_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    isbn: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    uri: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    access_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Verification
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(50),
        default=VerificationStatus.UNVERIFIED,
        nullable=False,
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


class ProvenanceRecord(Base):
    """Chain of custody for sources."""
    
    __tablename__ = "provenance_records"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=generate_uuid,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    retrieval_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    verification_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
