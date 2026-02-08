"""
AI Disclosure Controller - Progressive AI capability unlocks.
"""

import uuid
from enum import Enum
from typing import List, Set
from pydantic import BaseModel


class AILevel(int, Enum):
    """AI disclosure levels."""
    LEVEL_0 = 0  # No AI
    LEVEL_1 = 1  # Search Assistant
    LEVEL_2 = 2  # Structural Assistant
    LEVEL_3 = 3  # Drafting Assistant
    LEVEL_4 = 4  # Simulation Mode


class AICapability(str, Enum):
    """Individual AI capabilities."""
    
    # Level 1 - Search Assistant
    SEARCH_QUERIES = "search_queries"
    SOURCE_RECOMMENDATIONS = "source_recommendations"
    PDF_EXTRACTION = "pdf_extraction"
    
    # Level 2 - Structural Assistant
    OUTLINE_SUGGESTIONS = "outline_suggestions"
    GAP_ANALYSIS = "gap_analysis"
    CLAIM_EVIDENCE_LINKING = "claim_evidence_linking"
    
    # Level 3 - Drafting Assistant
    PARAGRAPH_SUGGESTIONS = "paragraph_suggestions"
    SOURCE_SUMMARIES = "source_summaries"
    METHOD_TEMPLATES = "method_templates"
    
    # Level 4 - Simulation Mode
    DEFENSE_QUESTIONS = "defense_questions"
    EXAMINER_SIMULATION = "examiner_simulation"
    CONTRADICTION_DETECTION = "contradiction_detection"


# Mapping of levels to capabilities
LEVEL_CAPABILITIES = {
    AILevel.LEVEL_0: set(),
    
    AILevel.LEVEL_1: {
        AICapability.SEARCH_QUERIES,
        AICapability.SOURCE_RECOMMENDATIONS,
        AICapability.PDF_EXTRACTION,
    },
    
    AILevel.LEVEL_2: {
        AICapability.SEARCH_QUERIES,
        AICapability.SOURCE_RECOMMENDATIONS,
        AICapability.PDF_EXTRACTION,
        AICapability.OUTLINE_SUGGESTIONS,
        AICapability.GAP_ANALYSIS,
        AICapability.CLAIM_EVIDENCE_LINKING,
    },
    
    AILevel.LEVEL_3: {
        AICapability.SEARCH_QUERIES,
        AICapability.SOURCE_RECOMMENDATIONS,
        AICapability.PDF_EXTRACTION,
        AICapability.OUTLINE_SUGGESTIONS,
        AICapability.GAP_ANALYSIS,
        AICapability.CLAIM_EVIDENCE_LINKING,
        AICapability.PARAGRAPH_SUGGESTIONS,
        AICapability.SOURCE_SUMMARIES,
        AICapability.METHOD_TEMPLATES,
    },
    
    AILevel.LEVEL_4: {
        AICapability.SEARCH_QUERIES,
        AICapability.SOURCE_RECOMMENDATIONS,
        AICapability.PDF_EXTRACTION,
        AICapability.OUTLINE_SUGGESTIONS,
        AICapability.GAP_ANALYSIS,
        AICapability.CLAIM_EVIDENCE_LINKING,
        AICapability.PARAGRAPH_SUGGESTIONS,
        AICapability.SOURCE_SUMMARIES,
        AICapability.METHOD_TEMPLATES,
        AICapability.DEFENSE_QUESTIONS,
        AICapability.EXAMINER_SIMULATION,
        AICapability.CONTRADICTION_DETECTION,
    },
}

# Level unlock requirements
LEVEL_REQUIREMENTS = {
    AILevel.LEVEL_0: "Default - no requirements",
    AILevel.LEVEL_1: "Pass Tier 1 checkpoint (80% on comprehension)",
    AILevel.LEVEL_2: "Pass Tier 2 checkpoint (3 prompts, 150 words each)",
    AILevel.LEVEL_3: "Write 5000+ words AND pass Tier 2",
    AILevel.LEVEL_4: "Pass Tier 3 checkpoint (85% on defense)",
}


class AIDisclosureController:
    """
    Controls what AI capabilities are available based on user's level.
    
    Progressive disclosure ensures users demonstrate understanding
    before accessing more powerful AI features.
    """
    
    @classmethod
    def get_available_capabilities(
        cls,
        ai_level: int,
    ) -> Set[AICapability]:
        """Get all capabilities available at a given level."""
        level = AILevel(min(ai_level, 4))
        return LEVEL_CAPABILITIES.get(level, set())
    
    @classmethod
    def has_capability(
        cls,
        ai_level: int,
        capability: AICapability,
    ) -> bool:
        """Check if a specific capability is available."""
        available = cls.get_available_capabilities(ai_level)
        return capability in available
    
    @classmethod
    def get_level_description(cls, ai_level: int) -> str:
        """Get description of what's unlocked at a level."""
        descriptions = {
            0: "No AI assistance available. Complete Tier 1 checkpoint to unlock.",
            1: "Search Assistant: Query suggestions, source recommendations, PDF extraction.",
            2: "Structural Assistant: Outline suggestions, gap analysis, claim-evidence linking.",
            3: "Drafting Assistant: Paragraph suggestions (40% edit required), source summaries.",
            4: "Simulation Mode: Defense questions, examiner simulation, contradiction detection.",
        }
        return descriptions.get(ai_level, "Unknown level")
    
    @classmethod
    def get_next_level_requirements(cls, ai_level: int) -> str:
        """Get requirements to unlock the next level."""
        next_level = min(ai_level + 1, 4)
        if next_level == ai_level:
            return "Maximum level reached"
        return LEVEL_REQUIREMENTS.get(AILevel(next_level), "")
    
    @classmethod
    def get_capability_restrictions(
        cls,
        capability: AICapability,
    ) -> dict:
        """
        Get restrictions/requirements for using a capability.
        
        Returns dict with:
        - min_level: Minimum AI level required
        - max_words: Maximum word output (if applicable)
        - requires_watermark: Whether output must be watermarked
        - min_modification: Minimum modification ratio required
        """
        restrictions = {
            AICapability.SEARCH_QUERIES: {
                "min_level": 1,
                "max_words": None,
                "requires_watermark": False,
                "min_modification": None,
            },
            AICapability.SOURCE_RECOMMENDATIONS: {
                "min_level": 1,
                "max_words": None,
                "requires_watermark": True,
                "min_modification": None,
            },
            AICapability.OUTLINE_SUGGESTIONS: {
                "min_level": 2,
                "max_words": 150,  # Per section
                "requires_watermark": True,
                "min_modification": 0.4,  # Must rewrite
            },
            AICapability.PARAGRAPH_SUGGESTIONS: {
                "min_level": 3,
                "max_words": 200,
                "requires_watermark": True,
                "min_modification": 0.4,  # >40% edit required
            },
            AICapability.SOURCE_SUMMARIES: {
                "min_level": 3,
                "max_words": 300,
                "requires_watermark": True,
                "min_modification": None,  # Checkbox required instead
            },
            AICapability.METHOD_TEMPLATES: {
                "min_level": 3,
                "max_words": 200,
                "requires_watermark": True,
                "min_modification": 0.4,
            },
            AICapability.DEFENSE_QUESTIONS: {
                "min_level": 4,
                "max_words": None,
                "requires_watermark": False,
                "min_modification": None,
            },
        }
        
        return restrictions.get(capability, {
            "min_level": 0,
            "max_words": None,
            "requires_watermark": False,
            "min_modification": None,
        })


class CapabilityRequest(BaseModel):
    """Request to use an AI capability."""
    
    capability: AICapability
    user_id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    context: str  # What the user wants help with


class CapabilityResponse(BaseModel):
    """Response indicating if capability can be used."""
    
    allowed: bool
    capability: AICapability
    reason: str
    restrictions: dict
