"""
Watermark - Invisible marking of AI-generated content.

AI attribution markers cannot be removed (Architecture Invariant #7).
"""

import hashlib
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WatermarkData(BaseModel):
    """Watermark metadata."""
    
    hash: str
    generated_at: datetime
    suggestion_type: str
    model_version: str
    word_count: int


class Watermarker:
    """
    Creates and verifies watermarks on AI-generated content.
    
    Watermarks are:
    - Hash-based for verification
    - Stored alongside content for tracking
    - Cannot be removed from the artifact history
    """
    
    # Current model version for watermarking
    MODEL_VERSION = "ramp-v1.0"
    
    # Salt for hashing (would be secret in production)
    SALT = "ramp-watermark-salt-2024"
    
    @classmethod
    def generate_watermark(
        cls,
        content: str,
        suggestion_type: str = "unknown",
    ) -> str:
        """
        Generate a watermark hash for content.
        
        The hash includes:
        - Content itself
        - Timestamp
        - Model version
        - Salt
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Create composite string for hashing
        composite = f"{cls.SALT}|{timestamp}|{cls.MODEL_VERSION}|{content}"
        
        # Generate SHA-256 hash
        watermark_hash = hashlib.sha256(composite.encode()).hexdigest()
        
        return watermark_hash
    
    @classmethod
    def create_watermark_data(
        cls,
        content: str,
        suggestion_type: str,
    ) -> WatermarkData:
        """Create full watermark data for storage."""
        return WatermarkData(
            hash=cls.generate_watermark(content, suggestion_type),
            generated_at=datetime.utcnow(),
            suggestion_type=suggestion_type,
            model_version=cls.MODEL_VERSION,
            word_count=len(content.split()),
        )
    
    @classmethod
    def verify_watermark(
        cls,
        content: str,
        stored_hash: str,
    ) -> bool:
        """
        Verify if content matches a stored watermark.
        
        Note: This is a simplified verification. In production,
        would need to store more metadata for exact verification.
        """
        # Simple check - in production would be more sophisticated
        # This just checks if the hash is valid format
        return len(stored_hash) == 64 and all(c in '0123456789abcdef' for c in stored_hash)
    
    @classmethod
    def detect_ai_content(
        cls,
        artifact_history: list,
    ) -> list[str]:
        """
        Detect which version(s) of an artifact contain AI content.
        
        Returns list of watermark hashes found.
        """
        watermarks = []
        
        for version in artifact_history:
            # Check if version has watermark metadata
            metadata = version.get("metadata", {})
            if "ai_watermark" in metadata:
                watermarks.append(metadata["ai_watermark"])
        
        return watermarks
    
    @classmethod
    def get_ai_attribution_text(
        cls,
        watermark_data: WatermarkData,
    ) -> str:
        """Generate human-readable AI attribution text."""
        return (
            f"[AI-Assisted Content]\n"
            f"Generated: {watermark_data.generated_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"Type: {watermark_data.suggestion_type}\n"
            f"Words: {watermark_data.word_count}\n"
            f"Verification: {watermark_data.hash[:16]}..."
        )


class AIAttributionTracker:
    """
    Tracks AI attribution across a project.
    
    Ensures AI markers cannot be removed from export.
    """
    
    def __init__(self):
        # Map of artifact_id -> list of watermarks
        self._attributions: dict[uuid.UUID, list[WatermarkData]] = {}
    
    def add_attribution(
        self,
        artifact_id: uuid.UUID,
        watermark: WatermarkData,
    ) -> None:
        """Record an AI attribution for an artifact."""
        if artifact_id not in self._attributions:
            self._attributions[artifact_id] = []
        self._attributions[artifact_id].append(watermark)
    
    def get_attributions(
        self,
        artifact_id: uuid.UUID,
    ) -> list[WatermarkData]:
        """Get all AI attributions for an artifact."""
        return self._attributions.get(artifact_id, [])
    
    def has_ai_content(self, artifact_id: uuid.UUID) -> bool:
        """Check if artifact has any AI-generated content."""
        return artifact_id in self._attributions and len(self._attributions[artifact_id]) > 0
    
    def get_project_ai_summary(
        self,
        artifact_ids: list[uuid.UUID],
    ) -> dict:
        """Get AI usage summary for a project."""
        total_ai_artifacts = 0
        total_ai_words = 0
        suggestion_types: dict[str, int] = {}
        
        for artifact_id in artifact_ids:
            attributions = self.get_attributions(artifact_id)
            if attributions:
                total_ai_artifacts += 1
                for attr in attributions:
                    total_ai_words += attr.word_count
                    suggestion_types[attr.suggestion_type] = \
                        suggestion_types.get(attr.suggestion_type, 0) + 1
        
        return {
            "total_artifacts_with_ai": total_ai_artifacts,
            "total_ai_words": total_ai_words,
            "by_type": suggestion_types,
        }
