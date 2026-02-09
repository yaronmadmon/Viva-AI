"""
Shared AI types - breaks circular imports between sandbox and prose_limits.
"""

from enum import Enum


class SuggestionType(str, Enum):
    """Types of AI suggestions."""
    OUTLINE = "outline"
    CLAIM_REFINEMENT = "claim_refinement"
    SOURCE_RECOMMENDATION = "source_recommendation"
    GAP_ANALYSIS = "gap_analysis"
    COMPREHENSION_QUESTION = "comprehension_question"
    SOURCE_SUMMARY = "source_summary"
    PARAGRAPH_DRAFT = "paragraph_draft"
    METHOD_TEMPLATE = "method_template"
    DEFENSE_QUESTION = "defense_question"
    CONTRADICTION_FLAG = "contradiction_flag"

    # ── Harvard-level quality engines ────────────────────────────────────
    CLAIM_DISCIPLINE_AUDIT = "claim_discipline_audit"
    METHODOLOGY_STRESS_TEST = "methodology_stress_test"
    CONTRIBUTION_VALIDATOR = "contribution_validator"
    LITERATURE_CONFLICT_MAP = "literature_conflict_map"
    PEDAGOGICAL_ANNOTATION = "pedagogical_annotation"


class ClaimLevel(str, Enum):
    """Sentence-level claim classification (Phase 1 - Claim Discipline)."""
    DESCRIPTIVE = "descriptive"      # Reporting data/facts
    INFERENTIAL = "inferential"      # Drawing conclusions from evidence
    SPECULATIVE = "speculative"      # Projecting beyond evidence


class TensionType(str, Enum):
    """Types of literature tension (Phase 4 - Conflict Mapping)."""
    METHODOLOGICAL = "methodological"        # Disagreement on methods
    THEORETICAL = "theoretical"              # Conflicting theoretical positions
    EMPIRICAL = "empirical"                  # Contradictory empirical findings
    DEFINITIONAL = "definitional"            # Disagreement on definitions/scope
    INTERPRETIVE = "interpretive"            # Different interpretations of same data
