"""
Suggestion Queue - Manages AI suggestions lifecycle.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class SuggestionStatus(str, Enum):
    """Status of an AI suggestion."""
    PENDING = "pending"      # Generated, waiting for user action
    VIEWED = "viewed"        # User has seen it
    ACCEPTED = "accepted"    # User accepted (may be modified)
    REJECTED = "rejected"    # User rejected
    EXPIRED = "expired"      # Not acted upon in time


class AISuggestion(BaseModel):
    """An AI suggestion with tracking."""
    
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    
    # Content
    suggestion_type: str
    content: str
    watermark_hash: str
    confidence: float
    
    # Status
    status: SuggestionStatus = SuggestionStatus.PENDING
    
    # User interaction
    viewed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    user_modified_content: Optional[str] = None
    modification_ratio: Optional[float] = None
    
    # Timestamps
    generated_at: datetime
    expires_at: Optional[datetime] = None


class SuggestionQueue:
    """
    Manages the queue of AI suggestions.
    
    Tracks suggestion lifecycle and user interactions.
    """
    
    def __init__(self):
        # In-memory store (in production, use database)
        self._suggestions: Dict[uuid.UUID, AISuggestion] = {}
    
    def add_suggestion(self, suggestion: AISuggestion) -> None:
        """Add a suggestion to the queue."""
        self._suggestions[suggestion.id] = suggestion
    
    def get_suggestion(self, suggestion_id: uuid.UUID) -> Optional[AISuggestion]:
        """Get a suggestion by ID."""
        return self._suggestions.get(suggestion_id)
    
    def get_user_pending_suggestions(
        self,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[AISuggestion]:
        """Get all pending suggestions for a user."""
        suggestions = [
            s for s in self._suggestions.values()
            if s.user_id == user_id and s.status == SuggestionStatus.PENDING
        ]
        
        if project_id:
            suggestions = [s for s in suggestions if s.project_id == project_id]
        
        return sorted(suggestions, key=lambda s: s.generated_at, reverse=True)
    
    def mark_viewed(self, suggestion_id: uuid.UUID) -> Optional[AISuggestion]:
        """Mark a suggestion as viewed."""
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion and suggestion.status == SuggestionStatus.PENDING:
            suggestion.status = SuggestionStatus.VIEWED
            suggestion.viewed_at = datetime.utcnow()
        return suggestion
    
    def accept_suggestion(
        self,
        suggestion_id: uuid.UUID,
        modified_content: str,
        modification_ratio: float,
    ) -> Optional[AISuggestion]:
        """Accept a suggestion with user modifications."""
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion:
            suggestion.status = SuggestionStatus.ACCEPTED
            suggestion.responded_at = datetime.utcnow()
            suggestion.user_modified_content = modified_content
            suggestion.modification_ratio = modification_ratio
        return suggestion
    
    def reject_suggestion(
        self,
        suggestion_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Optional[AISuggestion]:
        """Reject a suggestion."""
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion:
            suggestion.status = SuggestionStatus.REJECTED
            suggestion.responded_at = datetime.utcnow()
        return suggestion
    
    def get_suggestion_stats(
        self,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, int]:
        """Get suggestion statistics for a user/project."""
        suggestions = [
            s for s in self._suggestions.values()
            if s.user_id == user_id
        ]
        
        if project_id:
            suggestions = [s for s in suggestions if s.project_id == project_id]
        
        stats = {
            "total": len(suggestions),
            "pending": 0,
            "viewed": 0,
            "accepted": 0,
            "rejected": 0,
            "expired": 0,
        }
        
        for s in suggestions:
            stats[s.status.value] = stats.get(s.status.value, 0) + 1
        
        # Calculate acceptance rate
        responded = stats["accepted"] + stats["rejected"]
        if responded > 0:
            stats["acceptance_rate"] = stats["accepted"] / responded
        else:
            stats["acceptance_rate"] = 0.0
        
        return stats
    
    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Mark old pending suggestions as expired."""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_count = 0
        
        for suggestion in self._suggestions.values():
            if (suggestion.status == SuggestionStatus.PENDING and
                suggestion.generated_at < cutoff):
                suggestion.status = SuggestionStatus.EXPIRED
                expired_count += 1
        
        return expired_count
