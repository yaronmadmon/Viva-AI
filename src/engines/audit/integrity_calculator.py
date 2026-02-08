"""
Integrity Calculator - Calculates overall project integrity score.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.kernel.models.artifact import ContributionCategory
from src.engines.audit.contribution_scorer import ContributionScorer


class IssueSeverity(str, Enum):
    """Severity levels for integrity issues."""
    CRITICAL = "critical"  # Blocks export
    WARNING = "warning"    # Reduces score
    INFO = "info"          # No score impact


class IntegrityIssue(BaseModel):
    """An issue affecting integrity score."""
    
    severity: IssueSeverity
    category: str
    message: str
    artifact_id: Optional[uuid.UUID] = None
    score_impact: float = 0.0
    details: Optional[Dict[str, Any]] = None


class IntegrityScore(BaseModel):
    """Overall integrity score for a project."""
    
    project_id: uuid.UUID
    calculated_at: datetime
    
    # Overall score (0-100)
    score: float
    
    # Component scores
    contribution_score: float  # Based on AI modification ratios
    citation_score: float      # Based on citation verification
    structure_score: float     # Based on claim-evidence links
    mastery_score: float       # Based on checkpoint completion
    
    # Breakdown
    artifacts_analyzed: int
    primarily_human_count: int
    human_guided_count: int
    ai_reviewed_count: int
    unmodified_ai_count: int
    
    # Issues
    issues: List[IntegrityIssue]
    
    # Export decision
    export_allowed: bool
    blocking_issues: List[str]


class IntegrityCalculator:
    """
    Calculates project integrity scores.
    
    Score components:
    - Contribution (40%): Based on AI modification ratios
    - Citation (25%): Based on citation verification status
    - Structure (20%): Based on claim-evidence linking
    - Mastery (15%): Based on checkpoint completion
    
    Blocking criteria:
    - Score < 60%
    - Any unmodified AI content
    - Critical citation issues (non-existent DOIs)
    - Advisor override (logged, reduces score)
    """
    
    # Component weights
    CONTRIBUTION_WEIGHT = 0.40
    CITATION_WEIGHT = 0.25
    STRUCTURE_WEIGHT = 0.20
    MASTERY_WEIGHT = 0.15
    
    # Thresholds
    EXPORT_THRESHOLD = 60.0
    
    @classmethod
    def calculate_contribution_score(
        cls,
        artifact_categories: List[ContributionCategory],
    ) -> tuple[float, Dict[ContributionCategory, int]]:
        """
        Calculate contribution score from artifact categories.
        
        Returns score (0-100) and category counts.
        """
        if not artifact_categories:
            return 100.0, {}
        
        counts = {
            ContributionCategory.PRIMARILY_HUMAN: 0,
            ContributionCategory.HUMAN_GUIDED: 0,
            ContributionCategory.AI_REVIEWED: 0,
            ContributionCategory.UNMODIFIED_AI: 0,
        }
        
        total_points = 0.0
        for category in artifact_categories:
            counts[category] = counts.get(category, 0) + 1
            total_points += ContributionScorer.score_to_points(category)
        
        score = (total_points / len(artifact_categories)) * 100
        return round(score, 2), counts
    
    @classmethod
    def calculate_citation_score(
        cls,
        verified_count: int,
        unverified_count: int,
        flagged_count: int,
    ) -> float:
        """
        Calculate citation verification score.
        
        Returns score (0-100).
        """
        total = verified_count + unverified_count + flagged_count
        if total == 0:
            return 100.0  # No citations to verify
        
        # Verified = full points, unverified = half, flagged = zero
        points = verified_count * 1.0 + unverified_count * 0.5 + flagged_count * 0.0
        score = (points / total) * 100
        
        return round(score, 2)
    
    @classmethod
    def calculate_structure_score(
        cls,
        claims_count: int,
        claims_with_evidence: int,
        orphan_evidence_count: int,
    ) -> float:
        """
        Calculate structure score based on claim-evidence linking.
        
        Returns score (0-100).
        """
        if claims_count == 0:
            return 100.0  # No claims to link
        
        # Percentage of claims with evidence
        linked_ratio = claims_with_evidence / claims_count
        
        # Penalty for orphan evidence
        if orphan_evidence_count > 0:
            orphan_penalty = min(0.2, orphan_evidence_count * 0.05)
        else:
            orphan_penalty = 0.0
        
        score = (linked_ratio - orphan_penalty) * 100
        return round(max(0, score), 2)
    
    @classmethod
    def calculate_mastery_score(
        cls,
        tier_completed: int,
        has_advisor_override: bool,
    ) -> float:
        """
        Calculate mastery score based on checkpoint completion.
        
        Returns score (0-100).
        """
        # Base score from tier completion
        tier_scores = {
            0: 25.0,   # Not started
            1: 50.0,   # Tier 1 complete
            2: 75.0,   # Tier 2 complete
            3: 100.0,  # Tier 3 complete
        }
        
        score = tier_scores.get(tier_completed, 25.0)
        
        # Advisor override penalty
        if has_advisor_override:
            score *= 0.8  # 20% penalty
        
        return round(score, 2)
    
    @classmethod
    def calculate_overall(
        cls,
        project_id: uuid.UUID,
        artifact_categories: List[ContributionCategory],
        verified_citations: int,
        unverified_citations: int,
        flagged_citations: int,
        claims_count: int,
        claims_with_evidence: int,
        orphan_evidence: int,
        tier_completed: int,
        has_advisor_override: bool,
    ) -> IntegrityScore:
        """
        Calculate overall integrity score for a project.
        """
        issues: List[IntegrityIssue] = []
        blocking_issues: List[str] = []
        
        # Calculate component scores
        contribution_score, category_counts = cls.calculate_contribution_score(
            artifact_categories
        )
        citation_score = cls.calculate_citation_score(
            verified_citations, unverified_citations, flagged_citations
        )
        structure_score = cls.calculate_structure_score(
            claims_count, claims_with_evidence, orphan_evidence
        )
        mastery_score = cls.calculate_mastery_score(
            tier_completed, has_advisor_override
        )
        
        # Calculate weighted total
        overall_score = (
            contribution_score * cls.CONTRIBUTION_WEIGHT +
            citation_score * cls.CITATION_WEIGHT +
            structure_score * cls.STRUCTURE_WEIGHT +
            mastery_score * cls.MASTERY_WEIGHT
        )
        
        # Check for issues
        
        # Unmodified AI content
        unmodified_count = category_counts.get(ContributionCategory.UNMODIFIED_AI, 0)
        if unmodified_count > 0:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.CRITICAL,
                category="contribution",
                message=f"{unmodified_count} artifact(s) contain unmodified AI content",
                score_impact=-20.0,
            ))
            blocking_issues.append("Unmodified AI content detected")
        
        # AI-reviewed content warning
        ai_reviewed_count = category_counts.get(ContributionCategory.AI_REVIEWED, 0)
        if ai_reviewed_count > 0:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.WARNING,
                category="contribution",
                message=f"{ai_reviewed_count} artifact(s) have <30% user modification",
                score_impact=-5.0,
            ))
        
        # Flagged citations
        if flagged_citations > 0:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.CRITICAL,
                category="citation",
                message=f"{flagged_citations} citation(s) have critical issues",
                score_impact=-15.0,
            ))
            blocking_issues.append("Critical citation issues detected")
        
        # Unverified citations warning
        if unverified_citations > verified_citations:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.WARNING,
                category="citation",
                message=f"Majority of citations ({unverified_citations}) are unverified",
                score_impact=-5.0,
            ))
        
        # Claims without evidence
        claims_without = claims_count - claims_with_evidence
        if claims_without > 0:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.WARNING,
                category="structure",
                message=f"{claims_without} claim(s) have no linked evidence",
                score_impact=-3.0,
            ))
        
        # Advisor override
        if has_advisor_override:
            issues.append(IntegrityIssue(
                severity=IssueSeverity.INFO,
                category="mastery",
                message="Advisor override applied (reduces mastery score by 20%)",
                score_impact=0.0,
            ))
        
        # Determine if export allowed
        export_allowed = (
            len(blocking_issues) == 0 and
            overall_score >= cls.EXPORT_THRESHOLD
        )
        
        if overall_score < cls.EXPORT_THRESHOLD and not blocking_issues:
            blocking_issues.append(f"Score ({overall_score:.1f}%) below threshold ({cls.EXPORT_THRESHOLD}%)")
        
        return IntegrityScore(
            project_id=project_id,
            calculated_at=datetime.utcnow(),
            score=round(overall_score, 2),
            contribution_score=contribution_score,
            citation_score=citation_score,
            structure_score=structure_score,
            mastery_score=mastery_score,
            artifacts_analyzed=len(artifact_categories),
            primarily_human_count=category_counts.get(ContributionCategory.PRIMARILY_HUMAN, 0),
            human_guided_count=category_counts.get(ContributionCategory.HUMAN_GUIDED, 0),
            ai_reviewed_count=ai_reviewed_count,
            unmodified_ai_count=unmodified_count,
            issues=issues,
            export_allowed=export_allowed,
            blocking_issues=blocking_issues,
        )
