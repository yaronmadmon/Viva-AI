"""
Curriculum engine - Concept DAG, prerequisites, mastery signals.

Launch with one discipline and minimal Tier-aligned concept graph.
"""

from typing import Dict, List, Optional, Set

from pydantic import BaseModel


class Concept(BaseModel):
    """A concept in the curriculum."""

    id: str
    title: str
    tier: int = 1
    prerequisites: List[str] = []


class CurriculumEngine:
    """Curriculum DAG per discipline."""

    STEM_CONCEPTS: List[Concept] = [
        Concept(id="hypothesis", title="Hypothesis Formation", tier=1, prerequisites=[]),
        Concept(id="methods", title="Research Methods", tier=2, prerequisites=["hypothesis"]),
        Concept(id="evidence", title="Evidence & Citations", tier=2, prerequisites=["hypothesis"]),
        Concept(id="defense", title="Defense Readiness", tier=3, prerequisites=["methods", "evidence"]),
    ]

    _discipline_concepts: Dict[str, List[Concept]] = {
        "stem": STEM_CONCEPTS,
        "humanities": [
            Concept(id="argument", title="Argument Structure", tier=1, prerequisites=[]),
            Concept(id="sources", title="Primary Sources", tier=2, prerequisites=["argument"]),
        ],
        "social_sciences": STEM_CONCEPTS,
        "legal": STEM_CONCEPTS,
        "mixed": STEM_CONCEPTS,
    }

    @classmethod
    def get_concepts(cls, discipline: str) -> List[Concept]:
        """Return concepts for discipline."""
        return cls._discipline_concepts.get(discipline.lower(), cls.STEM_CONCEPTS)

    @classmethod
    def get_prerequisites(cls, concept_id: str, discipline: str) -> List[str]:
        """Return prerequisite concept IDs for a concept."""
        for c in cls.get_concepts(discipline):
            if c.id == concept_id:
                return c.prerequisites
        return []

    @classmethod
    def can_access(cls, concept_id: str, mastered_ids: Set[str], discipline: str) -> bool:
        """Check if user can access concept given mastered prerequisites."""
        prereqs = cls.get_prerequisites(concept_id, discipline)
        return all(p in mastered_ids for p in prereqs)


class LessonsEngine:
    """Reading -> practice -> assessment -> remediation."""

    @classmethod
    def get_lesson_structure(cls, discipline: str) -> List[dict]:
        """Return lesson structure for discipline."""
        concepts = CurriculumEngine.get_concepts(discipline)
        return [
            {
                "concept_id": c.id,
                "title": c.title,
                "tier": c.tier,
                "phases": ["reading", "practice", "assessment", "remediation"],
            }
            for c in concepts
        ]
