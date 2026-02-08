"""Unit tests for contribution scoring."""

import pytest

from src.kernel.models.artifact import ContributionCategory
from src.engines.audit.contribution_scorer import (
    ContributionScorer,
    calculate_modification_ratio,
)


class TestModificationRatio:
    """Tests for modification ratio calculation."""
    
    def test_identical_content(self):
        """Identical content should have 0 modification."""
        original = "This is some test content."
        modified = "This is some test content."
        
        ratio = calculate_modification_ratio(original, modified)
        assert ratio == 0.0
    
    def test_completely_different(self):
        """Completely different content should have high modification."""
        original = "Original content here."
        modified = "Totally rewritten text that shares nothing."
        
        ratio = calculate_modification_ratio(original, modified)
        assert ratio > 0.5  # algorithm-dependent; ensure clearly high modification
    
    def test_partial_modification(self):
        """Partial modification should be between 0 and 1."""
        original = "This is the original text that will be modified."
        modified = "This is the modified text that has been changed."
        
        ratio = calculate_modification_ratio(original, modified)
        assert 0.0 < ratio < 1.0
    
    def test_empty_original(self):
        """Empty original should return 1.0 (all new content)."""
        original = ""
        modified = "New content added."
        
        ratio = calculate_modification_ratio(original, modified)
        assert ratio == 1.0
    
    def test_whitespace_normalization(self):
        """Whitespace differences shouldn't affect ratio significantly."""
        original = "This   is    text."
        modified = "This is text."
        
        ratio = calculate_modification_ratio(original, modified)
        assert ratio < 0.1  # Very small modification


class TestContributionScorer:
    """Tests for ContributionScorer."""
    
    def test_primarily_human_category(self):
        """High modification should be categorized as primarily human."""
        original = "AI generated content."
        modified = "Completely rewritten by the user with entirely new ideas and different wording."
        
        analysis = ContributionScorer.analyze_contribution(original, modified)
        
        assert analysis.category == ContributionCategory.PRIMARILY_HUMAN
        assert analysis.is_acceptable is True
        assert analysis.blocks_export is False
    
    def test_human_guided_category(self):
        """Moderate modification should be categorized as human-guided."""
        original = "This is AI generated content that the user will modify."
        modified = "This is AI content that has been edited by the user."
        
        analysis = ContributionScorer.analyze_contribution(original, modified)
        
        assert analysis.category in [
            ContributionCategory.HUMAN_GUIDED,
            ContributionCategory.AI_REVIEWED,
        ]
        assert analysis.is_acceptable is True or analysis.requires_warning is True
    
    def test_unmodified_ai_category(self):
        """No modification should be categorized as unmodified AI."""
        original = "AI generated content that was not changed."
        modified = "AI generated content that was not changed."
        
        analysis = ContributionScorer.analyze_contribution(original, modified)
        
        assert analysis.category == ContributionCategory.UNMODIFIED_AI
        assert analysis.blocks_export is True
        assert analysis.is_acceptable is False
    
    def test_score_to_points(self):
        """Category to points conversion should be correct."""
        assert ContributionScorer.score_to_points(ContributionCategory.PRIMARILY_HUMAN) == 1.0
        assert ContributionScorer.score_to_points(ContributionCategory.HUMAN_GUIDED) == 0.8
        assert ContributionScorer.score_to_points(ContributionCategory.AI_REVIEWED) == 0.4
        assert ContributionScorer.score_to_points(ContributionCategory.UNMODIFIED_AI) == 0.0
