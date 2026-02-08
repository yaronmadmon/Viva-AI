"""
Humanities Discipline Pack - Literature, Philosophy, History, etc.

Characteristics:
- WARNING/SOFT validation for arguments
- Qualitative evidence accepted
- Interpretive claims supported
"""

from typing import Dict, List, Set

from src.kernel.models.artifact import ArtifactType, ClaimType, EvidenceType
from src.plugins.disciplines.base import (
    DisciplinePack,
    ValidationMode,
    ValidationRule,
    CitationRequirement,
    DefenseQuestionTemplate,
)


class HumanitiesPack(DisciplinePack):
    """
    Humanities discipline validation rules.
    
    Emphasizes:
    - Interpretive arguments
    - Textual analysis
    - Primary sources
    - Theoretical frameworks
    """
    
    @property
    def name(self) -> str:
        return "Humanities"
    
    @property
    def description(self) -> str:
        return "Literature, Philosophy, History, Arts, and related fields"
    
    @property
    def validation_rules(self) -> Dict[ArtifactType, ValidationRule]:
        return {
            ArtifactType.CLAIM: ValidationRule(
                artifact_type=ArtifactType.CLAIM,
                mode=ValidationMode.SOFT,
                description="Arguments should be supported by textual evidence",
                min_evidence_count=1,
            ),
            ArtifactType.METHOD: ValidationRule(
                artifact_type=ArtifactType.METHOD,
                mode=ValidationMode.SOFT,
                description="Theoretical framework should be explained",
            ),
            ArtifactType.EVIDENCE: ValidationRule(
                artifact_type=ArtifactType.EVIDENCE,
                mode=ValidationMode.WARNING,
                description="Qualitative and interpretive evidence accepted",
            ),
            ArtifactType.SOURCE: ValidationRule(
                artifact_type=ArtifactType.SOURCE,
                mode=ValidationMode.SOFT,
                description="Primary and secondary sources both valued",
            ),
            ArtifactType.DISCUSSION: ValidationRule(
                artifact_type=ArtifactType.DISCUSSION,
                mode=ValidationMode.WARNING,
                description="Should engage with alternative interpretations",
            ),
        }
    
    @property
    def citation_requirements(self) -> CitationRequirement:
        return CitationRequirement(
            style="MLA",  # Or Chicago depending on field
            require_doi=False,
            require_page_numbers=True,  # Important for textual analysis
            allow_websites=True,
            min_peer_reviewed_ratio=0.5,
        )
    
    @property
    def defense_questions(self) -> List[DefenseQuestionTemplate]:
        return [
            DefenseQuestionTemplate(
                topic="interpretation",
                question_template="How do you respond to an alternative reading of {text}?",
                expected_elements=["acknowledge_alternative", "defend_reading", "textual_support"],
            ),
            DefenseQuestionTemplate(
                topic="theoretical_framework",
                question_template="Why is {theory} the appropriate lens for this analysis?",
                expected_elements=["framework_fit", "alternatives_considered", "limitations"],
            ),
            DefenseQuestionTemplate(
                topic="contribution",
                question_template="What new understanding does your work provide?",
                expected_elements=["originality", "field_impact", "future_directions"],
            ),
        ]
    
    def get_required_evidence(self, claim_type: ClaimType) -> Set[EvidenceType]:
        """Humanities accepts qualitative and citation evidence."""
        if claim_type == ClaimType.INTERPRETATION:
            return {EvidenceType.QUALITATIVE, EvidenceType.CITATION}
        elif claim_type == ClaimType.ARGUMENT:
            return {EvidenceType.CITATION}
        return {EvidenceType.QUALITATIVE}
