"""
Prose Limits - Enforced limits on AI-generated content.

From the architecture spec:
- Source Summary: 300 words, watermarked, checkbox required
- Outline Expansion: 150 words/section, must rewrite
- Method Template: 200 words, >40% modification required
- Results Draft: BLOCKED
- Discussion Draft: 100 words/subsection, must expand 3x
"""

from typing import Dict, Optional
from pydantic import BaseModel

from src.ai.types import SuggestionType


class ProseLimit(BaseModel):
    """Limits for a specific content type."""
    
    suggestion_type: SuggestionType
    max_words: Optional[int]
    watermark_required: bool = True
    checkbox_required: bool = False
    min_modification: Optional[float] = None  # 0.0-1.0
    expand_factor: Optional[float] = None     # User must expand by this factor
    blocked: bool = False
    description: str = ""


# Default prose limits from architecture spec
DEFAULT_LIMITS: Dict[SuggestionType, ProseLimit] = {
    SuggestionType.SOURCE_SUMMARY: ProseLimit(
        suggestion_type=SuggestionType.SOURCE_SUMMARY,
        max_words=300,
        watermark_required=True,
        checkbox_required=True,
        description="AI-generated source summary. Must verify accuracy.",
    ),
    SuggestionType.OUTLINE: ProseLimit(
        suggestion_type=SuggestionType.OUTLINE,
        max_words=150,  # Per section
        watermark_required=True,
        min_modification=0.4,  # Must rewrite >40%
        description="Outline suggestion. Must be substantially rewritten.",
    ),
    SuggestionType.METHOD_TEMPLATE: ProseLimit(
        suggestion_type=SuggestionType.METHOD_TEMPLATE,
        max_words=200,
        watermark_required=True,
        min_modification=0.4,
        description="Method template. Must modify >40%.",
    ),
    SuggestionType.PARAGRAPH_DRAFT: ProseLimit(
        suggestion_type=SuggestionType.PARAGRAPH_DRAFT,
        max_words=200,
        watermark_required=True,
        min_modification=0.4,
        description="Paragraph suggestion. Must modify >40%.",
    ),
    # Results drafts are BLOCKED
    # Note: There's no SuggestionType for this - it's blocked at the capability level
    SuggestionType.GAP_ANALYSIS: ProseLimit(
        suggestion_type=SuggestionType.GAP_ANALYSIS,
        max_words=None,  # No limit - advisory only
        watermark_required=False,
        description="Gap analysis. Advisory only, not included in output.",
    ),
    SuggestionType.CLAIM_REFINEMENT: ProseLimit(
        suggestion_type=SuggestionType.CLAIM_REFINEMENT,
        max_words=100,
        watermark_required=True,
        min_modification=0.5,  # Must substantially modify
        description="Claim refinement suggestion. Shown as diff.",
    ),
    SuggestionType.SOURCE_RECOMMENDATION: ProseLimit(
        suggestion_type=SuggestionType.SOURCE_RECOMMENDATION,
        max_words=None,
        watermark_required=True,
        description="Source recommendations. Flagged as AI-suggested, unverified.",
    ),
    SuggestionType.COMPREHENSION_QUESTION: ProseLimit(
        suggestion_type=SuggestionType.COMPREHENSION_QUESTION,
        max_words=None,
        watermark_required=False,  # Questions don't need watermark
        description="Comprehension questions for mastery checkpoints.",
    ),
    SuggestionType.DEFENSE_QUESTION: ProseLimit(
        suggestion_type=SuggestionType.DEFENSE_QUESTION,
        max_words=None,
        watermark_required=False,
        description="Simulated examiner questions for defense prep.",
    ),
    SuggestionType.CONTRADICTION_FLAG: ProseLimit(
        suggestion_type=SuggestionType.CONTRADICTION_FLAG,
        max_words=None,
        watermark_required=False,
        description="Contradiction detection. Flags for review only.",
    ),

    # ── Harvard-level quality engines ────────────────────────────────────
    SuggestionType.CLAIM_DISCIPLINE_AUDIT: ProseLimit(
        suggestion_type=SuggestionType.CLAIM_DISCIPLINE_AUDIT,
        max_words=None,
        watermark_required=False,
        description="Claim discipline audit. Classifies sentences and flags overreach. Advisory only.",
    ),
    SuggestionType.METHODOLOGY_STRESS_TEST: ProseLimit(
        suggestion_type=SuggestionType.METHODOLOGY_STRESS_TEST,
        max_words=None,
        watermark_required=False,
        description="Methodology stress test. Generates examiner questions and flags missing defenses.",
    ),
    SuggestionType.CONTRIBUTION_VALIDATOR: ProseLimit(
        suggestion_type=SuggestionType.CONTRIBUTION_VALIDATOR,
        max_words=None,
        watermark_required=False,
        description="Contribution validator. Checks precision, falsifiability, and 'before vs after' framing.",
    ),
    SuggestionType.LITERATURE_CONFLICT_MAP: ProseLimit(
        suggestion_type=SuggestionType.LITERATURE_CONFLICT_MAP,
        max_words=None,
        watermark_required=False,
        description="Literature conflict mapping. Detects named disagreements and tension score.",
    ),
    SuggestionType.PEDAGOGICAL_ANNOTATION: ProseLimit(
        suggestion_type=SuggestionType.PEDAGOGICAL_ANNOTATION,
        max_words=None,
        watermark_required=False,
        description="Pedagogical meta-commentary. Explains why each structural move was made.",
    ),
}


class ProseLimits:
    """
    Manages and enforces prose limits for AI content.
    """
    
    def __init__(self, custom_limits: Optional[Dict[SuggestionType, ProseLimit]] = None):
        self.limits = DEFAULT_LIMITS.copy()
        if custom_limits:
            self.limits.update(custom_limits)
    
    def get_limit(self, suggestion_type: SuggestionType) -> ProseLimit:
        """Get the limit for a suggestion type."""
        return self.limits.get(suggestion_type, ProseLimit(
            suggestion_type=suggestion_type,
            max_words=200,  # Default limit
            watermark_required=True,
            description="Default limit applied.",
        ))
    
    def is_blocked(self, suggestion_type: SuggestionType) -> bool:
        """Check if a suggestion type is blocked."""
        limit = self.limits.get(suggestion_type)
        return limit.blocked if limit else False
    
    def check_modification(
        self,
        suggestion_type: SuggestionType,
        modification_ratio: float,
    ) -> tuple[bool, str]:
        """
        Check if modification meets requirements.
        
        Returns (passes, message).
        """
        limit = self.get_limit(suggestion_type)
        
        if limit.min_modification is None:
            return True, "No modification requirement"
        
        if modification_ratio >= limit.min_modification:
            return True, f"Modification ({modification_ratio:.0%}) meets requirement ({limit.min_modification:.0%})"
        
        return False, f"Modification ({modification_ratio:.0%}) below requirement ({limit.min_modification:.0%})"
    
    def truncate_content(
        self,
        content: str,
        suggestion_type: SuggestionType,
    ) -> tuple[str, bool]:
        """
        Truncate content to meet word limit.
        
        Returns (content, was_truncated).
        """
        limit = self.get_limit(suggestion_type)
        
        if limit.max_words is None:
            return content, False
        
        words = content.split()
        if len(words) <= limit.max_words:
            return content, False
        
        truncated = " ".join(words[:limit.max_words]) + "..."
        return truncated, True
    
    def get_all_limits(self) -> Dict[str, dict]:
        """Get all limits as a dictionary for API responses."""
        return {
            lt.value: {
                "max_words": limit.max_words,
                "watermark_required": limit.watermark_required,
                "checkbox_required": limit.checkbox_required,
                "min_modification": limit.min_modification,
                "blocked": limit.blocked,
                "description": limit.description,
            }
            for lt, limit in self.limits.items()
        }
