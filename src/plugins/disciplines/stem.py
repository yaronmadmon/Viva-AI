"""
STEM Discipline Pack - Science, Technology, Engineering, Mathematics.

Characteristics:
- HARD validation for data claims and methodology
- Requires quantitative evidence
- Strict DOI requirements for citations
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


class STEMPack(DisciplinePack):
    """
    STEM discipline validation rules.
    
    Emphasizes:
    - Reproducibility
    - Quantitative evidence
    - Peer-reviewed sources
    - Clear methodology
    """
    
    @property
    def name(self) -> str:
        return "STEM"
    
    @property
    def description(self) -> str:
        return "Science, Technology, Engineering, and Mathematics"
    
    @property
    def validation_rules(self) -> Dict[ArtifactType, ValidationRule]:
        return {
            ArtifactType.CLAIM: ValidationRule(
                artifact_type=ArtifactType.CLAIM,
                mode=ValidationMode.HARD,
                description="Claims must be supported by quantitative evidence",
                min_evidence_count=1,
                required_evidence_types=[EvidenceType.QUANTITATIVE],
                max_certainty_score=40.0,  # Low tolerance for overreach
            ),
            ArtifactType.METHOD: ValidationRule(
                artifact_type=ArtifactType.METHOD,
                mode=ValidationMode.HARD,
                description="Methodology must be a defensive argument with rejected alternatives and failure conditions",
                required_fields=["approach", "data_collection", "analysis_method"],
                require_rejected_alternatives=2,
                require_failure_conditions=True,
                require_boundary_conditions=True,
            ),
            ArtifactType.RESULT: ValidationRule(
                artifact_type=ArtifactType.RESULT,
                mode=ValidationMode.HARD,
                description="Results must include statistical analysis",
                required_fields=["data", "statistical_tests"],
            ),
            ArtifactType.EVIDENCE: ValidationRule(
                artifact_type=ArtifactType.EVIDENCE,
                mode=ValidationMode.SOFT,
                description="Evidence should include raw data or clear derivation",
            ),
            ArtifactType.SOURCE: ValidationRule(
                artifact_type=ArtifactType.SOURCE,
                mode=ValidationMode.HARD,
                description="Sources must have DOI or be peer-reviewed",
            ),
            ArtifactType.SECTION: ValidationRule(
                artifact_type=ArtifactType.SECTION,
                mode=ValidationMode.SOFT,
                description="Sections must contain intellectual positioning and named disagreements",
                require_positioning=True,
                require_named_disagreements=3,
            ),
            ArtifactType.DISCUSSION: ValidationRule(
                artifact_type=ArtifactType.DISCUSSION,
                mode=ValidationMode.SOFT,
                description="Discussion must address limitations, connect to literature tensions, and scope claims carefully",
                max_certainty_score=35.0,
            ),
        }
    
    @property
    def citation_requirements(self) -> CitationRequirement:
        return CitationRequirement(
            style="APA",
            require_doi=True,
            require_page_numbers=False,
            allow_websites=False,  # Prefer peer-reviewed
            min_peer_reviewed_ratio=0.8,  # 80% must be peer-reviewed
        )
    
    @property
    def defense_questions(self) -> List[DefenseQuestionTemplate]:
        return [
            DefenseQuestionTemplate(
                topic="methodology",
                question_template="Why did you choose {method} over alternatives like {alternatives}?",
                expected_elements=["justification", "comparison", "limitations"],
            ),
            DefenseQuestionTemplate(
                topic="reproducibility",
                question_template="How would another researcher reproduce your results?",
                expected_elements=["data_availability", "code_availability", "step_by_step"],
            ),
            DefenseQuestionTemplate(
                topic="statistical_validity",
                question_template="Justify your choice of statistical tests and sample size.",
                expected_elements=["test_selection", "power_analysis", "assumptions"],
            ),
        ]
    
    def get_required_evidence(self, claim_type: ClaimType) -> Set[EvidenceType]:
        """STEM requires quantitative evidence for most claims."""
        if claim_type == ClaimType.FINDING:
            return {EvidenceType.QUANTITATIVE}
        elif claim_type == ClaimType.HYPOTHESIS:
            return {EvidenceType.QUANTITATIVE, EvidenceType.CITATION}
        return {EvidenceType.QUANTITATIVE}
