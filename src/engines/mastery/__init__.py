"""
Mastery Engine - Tiered checkpoints and progressive AI disclosure.

Tiers:
- Tier 1: Section Understanding (80% pass on 5 questions)
- Tier 2: Critical Analysis (3 prompts, 150 words each)
- Tier 3: Defense Readiness (85% pass on 10 questions)

AI Disclosure Levels:
- Level 0: No AI
- Level 1: Search Assistant
- Level 2: Structural Assistant  
- Level 3: Drafting Assistant
- Level 4: Simulation Mode
"""

from src.engines.mastery.checkpoint_service import (
    CheckpointService,
    CheckpointType,
    CheckpointResult,
)
from src.engines.mastery.progress_tracker import ProgressTracker, UserProgress
from src.engines.mastery.ai_disclosure_controller import (
    AIDisclosureController,
    AILevel,
    AICapability,
)
from src.engines.mastery.question_bank import QuestionBank, Question

__all__ = [
    "CheckpointService",
    "CheckpointType",
    "CheckpointResult",
    "ProgressTracker",
    "UserProgress",
    "AIDisclosureController",
    "AILevel",
    "AICapability",
    "QuestionBank",
    "Question",
]
