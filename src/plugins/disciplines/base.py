"""
Base Discipline Pack - Abstract interface for all disciplines.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel

from src.kernel.models.artifact import ArtifactType, ClaimType, EvidenceType


class ValidationMode(str, Enum):
    """Validation strictness modes."""
    HARD = "hard"        # Blocks progression, requires resolution
    SOFT = "soft"        # Warns, requires acknowledgment
    WARNING = "warning"  # Displays advisory, no block


class ValidationRule(BaseModel):
    """A validation rule for a specific artifact type."""
    
    artifact_type: ArtifactType
    mode: ValidationMode
    description: str
    required_fields: List[str] = []
    min_evidence_count: int = 0
    required_evidence_types: List[EvidenceType] = []


class CitationRequirement(BaseModel):
    """Citation format requirements."""
    
    style: str  # APA, MLA, Chicago, etc.
    require_doi: bool = False
    require_page_numbers: bool = False
    allow_websites: bool = True
    min_peer_reviewed_ratio: float = 0.0


class DefenseQuestionTemplate(BaseModel):
    """Template for defense questions."""
    
    topic: str
    question_template: str
    expected_elements: List[str]


class DisciplinePack(ABC):
    """
    Abstract base class for discipline-specific validation.
    
    Each discipline pack defines:
    - How strictly different artifact types are validated
    - What evidence is required for claims
    - Citation format requirements
    - Defense question templates
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Discipline name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Discipline description."""
        pass
    
    @property
    @abstractmethod
    def validation_rules(self) -> Dict[ArtifactType, ValidationRule]:
        """Validation rules by artifact type."""
        pass
    
    @property
    @abstractmethod
    def citation_requirements(self) -> CitationRequirement:
        """Citation format requirements."""
        pass
    
    @property
    def defense_questions(self) -> List[DefenseQuestionTemplate]:
        """Defense question templates (optional)."""
        return []
    
    def get_validation_mode(self, artifact_type: ArtifactType) -> ValidationMode:
        """Get validation mode for an artifact type."""
        rule = self.validation_rules.get(artifact_type)
        return rule.mode if rule else ValidationMode.WARNING
    
    def get_required_evidence(self, claim_type: ClaimType) -> Set[EvidenceType]:
        """Get required evidence types for a claim type."""
        # Default implementation - override in subclasses
        return set()
    
    def validate_artifact(
        self,
        artifact_type: ArtifactType,
        content: str,
        metadata: dict,
    ) -> tuple[bool, List[str]]:
        """
        Validate an artifact against discipline rules.
        
        Returns (is_valid, list_of_issues).
        """
        rule = self.validation_rules.get(artifact_type)
        if not rule:
            return True, []
        
        issues = []
        
        # Check required fields
        for field in rule.required_fields:
            if field not in metadata or not metadata[field]:
                issues.append(f"Missing required field: {field}")
        
        # Check content length
        if artifact_type == ArtifactType.CLAIM:
            if len(content.split()) < 10:
                issues.append("Claim is too short (minimum 10 words)")
        
        is_valid = len(issues) == 0 or rule.mode == ValidationMode.WARNING
        return is_valid, issues
