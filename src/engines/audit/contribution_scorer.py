"""
Contribution Scorer - Tracks human vs AI contribution.

Categories:
- Primarily Human (>70% modification): Full credit
- Human-Guided (30-70% modification): Acceptable
- AI-Reviewed (<30% modification): Warning, flagged
- Unmodified AI (0% modification): Blocks export
"""

import hashlib
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional, Tuple
from pydantic import BaseModel

from src.kernel.models.artifact import ContributionCategory


class ContributionAnalysis(BaseModel):
    """Analysis of human vs AI contribution."""
    
    original_content: str
    modified_content: str
    
    # Calculated metrics
    modification_ratio: float  # 0.0 = unmodified, 1.0 = completely rewritten
    characters_changed: int
    characters_added: int
    characters_removed: int
    
    # Category
    category: ContributionCategory
    
    # Flags
    is_acceptable: bool
    requires_warning: bool
    blocks_export: bool


def calculate_modification_ratio(
    original: str,
    modified: str,
) -> float:
    """
    Calculate the modification ratio between original and modified text.
    
    Uses SequenceMatcher to find similarity, then inverts to get modification.
    
    Returns:
        Float from 0.0 (identical) to 1.0 (completely different)
    """
    if not original:
        return 1.0  # All new content is "100% human"
    
    if not modified:
        return 0.0  # Deleted everything
    
    # Normalize whitespace
    original_normalized = " ".join(original.split())
    modified_normalized = " ".join(modified.split())
    
    # Calculate similarity
    similarity = SequenceMatcher(
        None,
        original_normalized,
        modified_normalized,
    ).ratio()
    
    # Invert to get modification ratio
    modification = 1.0 - similarity
    
    return round(modification, 4)


class ContributionScorer:
    """
    Scores content based on human contribution level.
    
    Thresholds:
    - >70% modification: Primarily Human
    - 30-70% modification: Human-Guided
    - <30% modification: AI-Reviewed (warning)
    - <1% modification: Unmodified AI (blocked)
    """
    
    # Category thresholds
    PRIMARILY_HUMAN_THRESHOLD = 0.70
    HUMAN_GUIDED_THRESHOLD = 0.30
    UNMODIFIED_THRESHOLD = 0.01
    
    @classmethod
    def analyze_contribution(
        cls,
        original_ai_content: str,
        user_modified_content: str,
    ) -> ContributionAnalysis:
        """
        Analyze the contribution level of user modifications.
        
        Args:
            original_ai_content: The original AI-generated content
            user_modified_content: The user's modified version
            
        Returns:
            ContributionAnalysis with category and metrics
        """
        modification_ratio = calculate_modification_ratio(
            original_ai_content,
            user_modified_content,
        )
        
        # Calculate character differences
        orig_len = len(original_ai_content)
        mod_len = len(user_modified_content)
        
        chars_changed = int(orig_len * (1 - SequenceMatcher(
            None, original_ai_content, user_modified_content
        ).ratio()))
        chars_added = max(0, mod_len - orig_len + chars_changed)
        chars_removed = max(0, orig_len - mod_len + chars_changed)
        
        # Determine category
        category = cls.categorize_modification(modification_ratio)
        
        # Determine flags
        is_acceptable = category in [
            ContributionCategory.PRIMARILY_HUMAN,
            ContributionCategory.HUMAN_GUIDED,
        ]
        requires_warning = category == ContributionCategory.AI_REVIEWED
        blocks_export = category == ContributionCategory.UNMODIFIED_AI
        
        return ContributionAnalysis(
            original_content=original_ai_content,
            modified_content=user_modified_content,
            modification_ratio=modification_ratio,
            characters_changed=chars_changed,
            characters_added=chars_added,
            characters_removed=chars_removed,
            category=category,
            is_acceptable=is_acceptable,
            requires_warning=requires_warning,
            blocks_export=blocks_export,
        )
    
    @classmethod
    def categorize_modification(
        cls,
        modification_ratio: float,
    ) -> ContributionCategory:
        """Categorize based on modification ratio."""
        if modification_ratio >= cls.PRIMARILY_HUMAN_THRESHOLD:
            return ContributionCategory.PRIMARILY_HUMAN
        elif modification_ratio >= cls.HUMAN_GUIDED_THRESHOLD:
            return ContributionCategory.HUMAN_GUIDED
        elif modification_ratio >= cls.UNMODIFIED_THRESHOLD:
            return ContributionCategory.AI_REVIEWED
        else:
            return ContributionCategory.UNMODIFIED_AI
    
    @classmethod
    def get_category_description(cls, category: ContributionCategory) -> str:
        """Get human-readable description of category."""
        descriptions = {
            ContributionCategory.PRIMARILY_HUMAN: 
                "Primarily Human-Authored: Content created from scratch or with >70% modification",
            ContributionCategory.HUMAN_GUIDED:
                "Human-Guided, AI-Assisted: Content with 30-70% user modification",
            ContributionCategory.AI_REVIEWED:
                "AI-Generated, Human-Reviewed: Content with <30% modification (warning)",
            ContributionCategory.UNMODIFIED_AI:
                "Unmodified AI: Verbatim AI content (blocks export)",
        }
        return descriptions.get(category, "Unknown category")
    
    @classmethod
    def score_to_points(cls, category: ContributionCategory) -> float:
        """Convert category to points for integrity calculation."""
        points = {
            ContributionCategory.PRIMARILY_HUMAN: 1.0,
            ContributionCategory.HUMAN_GUIDED: 0.8,
            ContributionCategory.AI_REVIEWED: 0.4,
            ContributionCategory.UNMODIFIED_AI: 0.0,
        }
        return points.get(category, 0.0)


class PasteDetector:
    """
    Detects potential paste events with AI-likelihood scoring.
    
    Flags suspicious patterns:
    - Large content additions in short time
    - Content matching AI-generated patterns
    - Rapid successive edits
    """
    
    # Thresholds
    LARGE_PASTE_CHARS = 500
    RAPID_EDIT_SECONDS = 5
    
    @classmethod
    def detect_paste(
        cls,
        previous_content: str,
        new_content: str,
        edit_duration_seconds: float,
    ) -> Tuple[bool, float]:
        """
        Detect if content was likely pasted.
        
        Returns:
            Tuple of (is_likely_paste, ai_likelihood_score)
        """
        chars_added = len(new_content) - len(previous_content)
        
        # Large content addition
        if chars_added > cls.LARGE_PASTE_CHARS:
            is_paste = True
            
            # Calculate AI likelihood (STUB - would use ML model)
            ai_likelihood = cls._estimate_ai_likelihood(
                new_content[len(previous_content):]
            )
            
            return is_paste, ai_likelihood
        
        # Rapid edit with significant change
        if edit_duration_seconds < cls.RAPID_EDIT_SECONDS and chars_added > 100:
            return True, 0.5  # Medium likelihood
        
        return False, 0.0
    
    @classmethod
    def _estimate_ai_likelihood(cls, text: str) -> float:
        """
        Estimate likelihood that text is AI-generated.
        
        STUB: Would use ML classifier in production.
        For now, uses simple heuristics.
        """
        # Simple heuristics (real would be ML-based)
        ai_indicators = 0
        total_checks = 5
        
        # Check for common AI patterns
        ai_phrases = [
            "it's important to note",
            "in conclusion",
            "this suggests that",
            "furthermore",
            "however, it should be noted",
        ]
        
        text_lower = text.lower()
        for phrase in ai_phrases:
            if phrase in text_lower:
                ai_indicators += 1
        
        return ai_indicators / total_checks
