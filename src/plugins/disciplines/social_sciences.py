"""
Social Sciences Discipline Pack - Psychology, Sociology, Economics, etc.

Characteristics:
- SOFT validation for mixed methods
- Both quantitative and qualitative evidence
- IRB/ethics considerations
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


class SocialSciencesPack(DisciplinePack):
    """
    Social Sciences discipline validation rules.
    
    Emphasizes:
    - Mixed methods research
    - Ethical considerations
    - Sampling and generalizability
    - Theoretical grounding
    """
    
    @property
    def name(self) -> str:
        return "Social Sciences"
    
    @property
    def description(self) -> str:
        return "Psychology, Sociology, Economics, Political Science, and related fields"
    
    @property
    def validation_rules(self) -> Dict[ArtifactType, ValidationRule]:
        return {
            ArtifactType.CLAIM: ValidationRule(
                artifact_type=ArtifactType.CLAIM,
                mode=ValidationMode.SOFT,
                description="Claims should be supported by appropriate evidence",
                min_evidence_count=1,
            ),
            ArtifactType.METHOD: ValidationRule(
                artifact_type=ArtifactType.METHOD,
                mode=ValidationMode.SOFT,
                description="Methodology must address sampling and ethics",
                required_fields=["participants", "ethics_approval"],
            ),
            ArtifactType.RESULT: ValidationRule(
                artifact_type=ArtifactType.RESULT,
                mode=ValidationMode.SOFT,
                description="Results should address statistical or thematic analysis",
            ),
            ArtifactType.EVIDENCE: ValidationRule(
                artifact_type=ArtifactType.EVIDENCE,
                mode=ValidationMode.SOFT,
                description="Mixed methods evidence accepted",
            ),
            ArtifactType.SOURCE: ValidationRule(
                artifact_type=ArtifactType.SOURCE,
                mode=ValidationMode.SOFT,
                description="Peer-reviewed sources preferred",
            ),
        }
    
    @property
    def citation_requirements(self) -> CitationRequirement:
        return CitationRequirement(
            style="APA",
            require_doi=False,  # Preferred but not required
            require_page_numbers=False,
            allow_websites=True,  # Government data, etc.
            min_peer_reviewed_ratio=0.6,
        )
    
    @property
    def defense_questions(self) -> List[DefenseQuestionTemplate]:
        return [
            DefenseQuestionTemplate(
                topic="generalizability",
                question_template="To what extent can your findings be generalized beyond your sample?",
                expected_elements=["sample_limitations", "population_fit", "external_validity"],
            ),
            DefenseQuestionTemplate(
                topic="ethics",
                question_template="How did you address ethical considerations in your research?",
                expected_elements=["irb_approval", "informed_consent", "participant_protection"],
            ),
            DefenseQuestionTemplate(
                topic="mixed_methods",
                question_template="How do your quantitative and qualitative findings complement each other?",
                expected_elements=["triangulation", "convergence", "divergence_explanation"],
            ),
        ]
    
    def get_required_evidence(self, claim_type: ClaimType) -> Set[EvidenceType]:
        """Social sciences accepts mixed evidence."""
        if claim_type == ClaimType.FINDING:
            return {EvidenceType.MIXED}
        elif claim_type == ClaimType.HYPOTHESIS:
            return {EvidenceType.QUANTITATIVE, EvidenceType.QUALITATIVE}
        return {EvidenceType.MIXED}
