"""
Export Controller - Decides if project can be exported.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from src.engines.audit.integrity_calculator import IntegrityScore


class ExportBlockReason(str, Enum):
    """Reasons export might be blocked."""
    LOW_INTEGRITY_SCORE = "low_integrity_score"
    UNMODIFIED_AI_CONTENT = "unmodified_ai_content"
    CRITICAL_CITATION_ISSUES = "critical_citation_issues"
    MASTERY_NOT_COMPLETED = "mastery_not_completed"
    PROJECT_NOT_SUBMITTED = "project_not_submitted"
    PENDING_REVIEWS = "pending_reviews"
    CURRICULUM_INCOMPLETE = "curriculum_incomplete"


class ExportDecision(BaseModel):
    """Decision on whether export is allowed."""
    
    project_id: uuid.UUID
    decided_at: datetime
    
    allowed: bool
    reasons: List[ExportBlockReason]
    messages: List[str]
    
    # Integrity info
    integrity_score: float
    integrity_threshold: float
    
    # Actions user can take
    recommended_actions: List[str]


class ExportController:
    """
    Controls project export based on integrity and completion status.
    
    Export is blocked if:
    - Integrity score < 60%
    - Any unmodified AI content exists
    - Critical citation issues (non-existent DOIs, major mismatches)
    - Tier 3 mastery checkpoint not completed (for full export)
    """
    
    INTEGRITY_THRESHOLD = 60.0
    
    @classmethod
    def evaluate_export_readiness(
        cls,
        project_id: uuid.UUID,
        integrity_score: IntegrityScore,
        mastery_tier: int,
        project_status: str,
        pending_reviews: int = 0,
        curriculum_mastered: bool = True,
        missing_concepts: Optional[List[str]] = None,
    ) -> ExportDecision:
        """
        Evaluate if a project is ready for export.
        
        Args:
            project_id: The project ID
            integrity_score: Calculated integrity score
            mastery_tier: User's current mastery tier
            project_status: Project status (draft/active/submitted/archived)
            pending_reviews: Number of pending review requests
            
        Returns:
            ExportDecision with allowed status and reasons
        """
        reasons: List[ExportBlockReason] = []
        messages: List[str] = []
        actions: List[str] = []
        
        # Check integrity score
        if integrity_score.score < cls.INTEGRITY_THRESHOLD:
            reasons.append(ExportBlockReason.LOW_INTEGRITY_SCORE)
            messages.append(
                f"Integrity score ({integrity_score.score:.1f}%) is below "
                f"threshold ({cls.INTEGRITY_THRESHOLD}%)"
            )
            actions.append("Review and address integrity issues in the integrity report")
        
        # Check for unmodified AI
        if integrity_score.unmodified_ai_count > 0:
            reasons.append(ExportBlockReason.UNMODIFIED_AI_CONTENT)
            messages.append(
                f"{integrity_score.unmodified_ai_count} artifact(s) contain "
                "unmodified AI content"
            )
            actions.append("Edit artifacts flagged as 'Unmodified AI' to add your modifications")
        
        # Check for critical issues from integrity calculation
        for issue in integrity_score.issues:
            if issue.severity.value == "critical" and issue.category == "citation":
                if ExportBlockReason.CRITICAL_CITATION_ISSUES not in reasons:
                    reasons.append(ExportBlockReason.CRITICAL_CITATION_ISSUES)
                    messages.append("Critical citation issues detected")
                    actions.append("Verify and fix flagged citations")
        
        # Check mastery completion (for full export)
        if mastery_tier < 3:
            reasons.append(ExportBlockReason.MASTERY_NOT_COMPLETED)
            messages.append(
                f"Mastery Tier 3 not completed (current: Tier {mastery_tier})"
            )
            actions.append("Complete Tier 3 defense readiness checkpoint")
        
        # Check project status
        if project_status == "draft":
            reasons.append(ExportBlockReason.PROJECT_NOT_SUBMITTED)
            messages.append("Project is still in draft status")
            actions.append("Change project status to 'submitted' when ready")
        
        # Check pending reviews
        if pending_reviews > 0:
            reasons.append(ExportBlockReason.PENDING_REVIEWS)
            messages.append(f"{pending_reviews} review request(s) are pending")
            actions.append("Wait for or cancel pending review requests")

        # Check curriculum completion
        if not curriculum_mastered:
            reasons.append(ExportBlockReason.CURRICULUM_INCOMPLETE)
            missing = missing_concepts or []
            messages.append(f"Curriculum incomplete: {', '.join(missing) or 'required concepts not mastered'}")
            actions.append("Complete required curriculum concepts")

        # Determine if allowed
        # Allow if only MASTERY_NOT_COMPLETED or PROJECT_NOT_SUBMITTED
        # (these are soft blocks that can be overridden)
        hard_blocks = [
            ExportBlockReason.LOW_INTEGRITY_SCORE,
            ExportBlockReason.UNMODIFIED_AI_CONTENT,
            ExportBlockReason.CRITICAL_CITATION_ISSUES,
        ]
        
        allowed = not any(r in hard_blocks for r in reasons)
        
        return ExportDecision(
            project_id=project_id,
            decided_at=datetime.utcnow(),
            allowed=allowed,
            reasons=reasons,
            messages=messages,
            integrity_score=integrity_score.score,
            integrity_threshold=cls.INTEGRITY_THRESHOLD,
            recommended_actions=actions,
        )
    
    @classmethod
    def generate_integrity_certificate(
        cls,
        project_id: uuid.UUID,
        project_title: str,
        author_name: str,
        integrity_score: IntegrityScore,
        export_decision: ExportDecision,
    ) -> dict:
        """
        Generate an integrity certificate for the export.
        
        This is included in exported documents and can be verified.
        """
        import hashlib
        
        # Create certificate data
        cert_data = {
            "project_id": str(project_id),
            "title": project_title,
            "author": author_name,
            "generated_at": datetime.utcnow().isoformat(),
            "integrity_score": integrity_score.score,
            "contribution_breakdown": {
                "primarily_human": integrity_score.primarily_human_count,
                "human_guided": integrity_score.human_guided_count,
                "ai_reviewed": integrity_score.ai_reviewed_count,
                "unmodified_ai": integrity_score.unmodified_ai_count,
            },
            "component_scores": {
                "contribution": integrity_score.contribution_score,
                "citation": integrity_score.citation_score,
                "structure": integrity_score.structure_score,
                "mastery": integrity_score.mastery_score,
            },
            "artifacts_analyzed": integrity_score.artifacts_analyzed,
            "export_allowed": export_decision.allowed,
        }
        
        # Generate verification hash
        cert_string = str(sorted(cert_data.items()))
        cert_hash = hashlib.sha256(cert_string.encode()).hexdigest()
        
        cert_data["verification_hash"] = cert_hash
        cert_data["verification_url"] = f"https://ramp.example.com/verify/{cert_hash[:16]}"
        
        return cert_data
