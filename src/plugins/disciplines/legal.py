"""
Legal Discipline Pack - Law, Legal Studies.

Characteristics:
- HARD validation for case citations
- Specific citation format (Bluebook, OSCOLA)
- Precedent-based argumentation
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


class LegalPack(DisciplinePack):
    """
    Legal discipline validation rules.
    
    Emphasizes:
    - Case law citations
    - Statutory interpretation
    - Precedent analysis
    - Jurisdictional awareness
    """
    
    @property
    def name(self) -> str:
        return "Legal"
    
    @property
    def description(self) -> str:
        return "Law, Legal Studies, and Jurisprudence"
    
    @property
    def validation_rules(self) -> Dict[ArtifactType, ValidationRule]:
        return {
            ArtifactType.CLAIM: ValidationRule(
                artifact_type=ArtifactType.CLAIM,
                mode=ValidationMode.HARD,
                description="Legal claims must cite authority",
                min_evidence_count=1,
                required_evidence_types=[EvidenceType.CITATION],
                max_certainty_score=40.0,
            ),
            ArtifactType.METHOD: ValidationRule(
                artifact_type=ArtifactType.METHOD,
                mode=ValidationMode.SOFT,
                description="Legal methodology must specify jurisdiction and justify approach against alternatives",
                required_fields=["jurisdiction", "legal_framework"],
                require_rejected_alternatives=1,
                require_boundary_conditions=True,
            ),
            ArtifactType.EVIDENCE: ValidationRule(
                artifact_type=ArtifactType.EVIDENCE,
                mode=ValidationMode.HARD,
                description="Evidence must be properly cited legal authority",
            ),
            ArtifactType.SOURCE: ValidationRule(
                artifact_type=ArtifactType.SOURCE,
                mode=ValidationMode.HARD,
                description="Sources must use proper legal citation format",
            ),
            ArtifactType.SECTION: ValidationRule(
                artifact_type=ArtifactType.SECTION,
                mode=ValidationMode.SOFT,
                description="Sections must contain doctrinal positioning and named scholarly disagreements",
                require_positioning=True,
                require_named_disagreements=3,
            ),
        }
    
    @property
    def citation_requirements(self) -> CitationRequirement:
        return CitationRequirement(
            style="Bluebook",  # US; OSCOLA for UK
            require_doi=False,
            require_page_numbers=True,  # Pin cites required
            allow_websites=True,  # For statutes, regulations
            min_peer_reviewed_ratio=0.3,  # Case law and statutes aren't "peer-reviewed"
        )
    
    @property
    def defense_questions(self) -> List[DefenseQuestionTemplate]:
        return [
            DefenseQuestionTemplate(
                topic="precedent",
                question_template="How does {case} affect your argument? Is it distinguishable?",
                expected_elements=["case_analysis", "distinguishing_factors", "binding_authority"],
            ),
            DefenseQuestionTemplate(
                topic="jurisdiction",
                question_template="How would your analysis change in a different jurisdiction?",
                expected_elements=["jurisdictional_differences", "comparative_law", "universal_principles"],
            ),
            DefenseQuestionTemplate(
                topic="policy",
                question_template="What are the policy implications of your proposed interpretation?",
                expected_elements=["practical_impact", "stakeholder_analysis", "unintended_consequences"],
            ),
        ]
    
    def get_required_evidence(self, claim_type: ClaimType) -> Set[EvidenceType]:
        """Legal requires citation evidence for all claims."""
        return {EvidenceType.CITATION}
    
    def validate_artifact(
        self,
        artifact_type: ArtifactType,
        content: str,
        metadata: dict,
    ) -> tuple[bool, List[str]]:
        """Legal-specific validation with citation checking."""
        is_valid, issues = super().validate_artifact(artifact_type, content, metadata)
        
        # Additional legal-specific checks
        if artifact_type == ArtifactType.SOURCE:
            # Check for legal citation patterns
            legal_patterns = ["v.", "§", "U.S.C.", "F.2d", "F.3d", "S.Ct."]
            has_legal_cite = any(p in content for p in legal_patterns)
            
            if not has_legal_cite and "url" not in metadata:
                issues.append("Legal source should have proper case/statute citation")
        
        return len(issues) == 0, issues
