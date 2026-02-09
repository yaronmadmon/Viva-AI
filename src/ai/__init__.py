"""
AI Isolation Zone - Sandboxed AI capabilities.

All AI interactions are:
- Logged before and after
- Watermarked for tracking
- Subject to prose limits
- Validated before surfacing to users
"""

from src.ai.types import SuggestionType
from src.ai.sandbox import AISandbox
from src.ai.suggestion_queue import SuggestionQueue, AISuggestion, SuggestionStatus
from src.ai.prose_limits import ProseLimits, ProseLimit
from src.ai.watermark import Watermarker

__all__ = [
    "AISandbox",
    "SuggestionType",
    "SuggestionQueue",
    "AISuggestion",
    "SuggestionStatus",
    "ProseLimits",
    "ProseLimit",
    "Watermarker",
]
