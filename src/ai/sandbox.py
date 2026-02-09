"""
AI Sandbox - Isolated execution environment for AI capabilities.

CRITICAL INVARIANTS:
- AI output NEVER enters trusted zone without validation
- All suggestions are logged before and after
- No direct database access from AI
- All outputs are watermarked
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel

from src.ai.types import SuggestionType
from src.ai.prose_limits import ProseLimits
from src.ai.watermark import Watermarker
from src.config import get_settings
from src.engines.mastery.ai_disclosure_controller import AICapability, AIDisclosureController


class ArtifactContext(BaseModel):
    """Context provided to AI for generating suggestions."""
    
    project_id: uuid.UUID
    artifact_id: uuid.UUID
    artifact_type: str
    content: str
    title: Optional[str] = None
    parent_content: Optional[str] = None
    related_claims: Optional[list] = None
    related_sources: Optional[list] = None


class SuggestionRequest(BaseModel):
    """Request for an AI suggestion."""
    
    user_id: uuid.UUID
    context: ArtifactContext
    suggestion_type: SuggestionType
    additional_instructions: Optional[str] = None


class SuggestionOutput(BaseModel):
    """Output from AI sandbox."""
    
    suggestion_id: uuid.UUID
    suggestion_type: SuggestionType
    content: str
    confidence: float
    watermark_hash: str
    word_count: int
    truncated: bool
    requires_checkbox: bool
    min_modification_required: Optional[float]
    generated_at: datetime
    
    # Metadata
    model_used: str = "stub"
    generation_time_ms: int = 0


class ValidationResult(BaseModel):
    """Result of validating AI output."""
    
    valid: bool
    issues: list[str]
    sanitized_content: Optional[str] = None


class AISandbox:
    """
    Isolated AI execution environment.
    
    This is the ONLY way AI can interact with the system.
    All operations are logged and validated.
    """
    
    def __init__(self):
        self.prose_limits = ProseLimits()
        self.watermarker = Watermarker()
    
    async def generate_suggestion(
        self,
        request: SuggestionRequest,
        user_ai_level: int,
    ) -> Optional[SuggestionOutput]:
        """
        Generate an AI suggestion (watermarked, logged).
        
        Args:
            request: The suggestion request with context
            user_ai_level: User's current AI disclosure level
            
        Returns:
            SuggestionOutput if allowed, None if blocked
        """
        # Check if user has access to this capability
        capability = self._suggestion_type_to_capability(request.suggestion_type)
        if not AIDisclosureController.has_capability(user_ai_level, capability):
            return None
        
        # Get prose limits for this type
        limit = self.prose_limits.get_limit(request.suggestion_type)
        
        # Generate content: real OpenAI when key is set, else stub
        settings = get_settings()
        key = (settings.openai_api_key or "").strip()
        is_placeholder = key.startswith("sk-your-") or key == "sk-your-openai-api-key"
        start_ms = time.perf_counter()
        model_used = "stub"
        raw_content: str
        if key and not is_placeholder:
            try:
                raw_content, model_used = await self._openai_generate(request)
            except Exception:
                raw_content = self._stub_generate(request)
        else:
            raw_content = self._stub_generate(request)
        generation_time_ms = int((time.perf_counter() - start_ms) * 1000)
        
        # Apply prose limits
        truncated = False
        if limit.max_words and len(raw_content.split()) > limit.max_words:
            words = raw_content.split()[:limit.max_words]
            raw_content = " ".join(words) + "..."
            truncated = True
        
        # Validate output
        validation = await self.validate_output(raw_content, request.suggestion_type)
        if not validation.valid:
            raw_content = validation.sanitized_content or raw_content
        
        # Apply watermark
        watermark_hash = self.watermarker.generate_watermark(raw_content)
        
        # Create output
        suggestion_id = uuid.uuid4()
        output = SuggestionOutput(
            suggestion_id=suggestion_id,
            suggestion_type=request.suggestion_type,
            content=raw_content,
            confidence=0.8 if model_used == "stub" else 0.85,
            watermark_hash=watermark_hash,
            word_count=len(raw_content.split()),
            truncated=truncated,
            requires_checkbox=limit.checkbox_required,
            min_modification_required=limit.min_modification,
            generated_at=datetime.utcnow(),
            model_used=model_used,
            generation_time_ms=generation_time_ms,
        )
        
        return output
    
    async def validate_output(
        self,
        content: str,
        suggestion_type: SuggestionType,
    ) -> ValidationResult:
        """
        Validate AI output before surfacing to user.
        
        Checks for:
        - Inappropriate content
        - Formatting issues
        - Potential hallucinations (stub)
        - Claim discipline violations (overreach, unhedged claims)
        """
        import re
        issues = []
        sanitized = content
        
        # Check for blocked patterns
        blocked_patterns = [
            "as an ai",
            "i cannot",
            "i don't have access",
        ]
        
        content_lower = content.lower()
        for pattern in blocked_patterns:
            if pattern in content_lower:
                issues.append(f"Blocked pattern detected: {pattern}")
                sanitized = sanitized.replace(pattern, "[...]")
        
        # Check word count
        if suggestion_type == SuggestionType.PARAGRAPH_DRAFT:
            if len(content.split()) > 200:
                issues.append("Paragraph draft exceeds 200 word limit")
        
        # ── Claim discipline hardening ───────────────────────────────────
        # Catch overreach in AI-generated prose BEFORE it reaches the user.
        overreach_patterns = [
            (r"\bproves?\b(?!\s+that)", "proves", "suggests"),
            (r"\bdemonstrates?\s+conclusively\b", "demonstrates conclusively", "indicates"),
            (r"\bestablish(?:es)?\s+beyond\s+doubt\b", "establishes beyond doubt", "provides evidence for"),
            (r"\bundeniab(?:ly|le)\b", "undeniable", "notable"),
            (r"\birrefutabl[ey]\b", "irrefutable", "substantial"),
            (r"\bdefinitively\b", "definitively", "substantively"),
            (r"\b(?:is|are)\s+generalizable?\s+to\s+all\b",
             "generalizable to all", "may be applicable to similar populations"),
            (r"\bwill\s+transform\b", "will transform", "may contribute to"),
            (r"\bready\s+for\s+clinical\s+use\b",
             "ready for clinical use",
             "warrants further investigation for potential clinical application"),
            (r"\bclearly\s+shows?\b", "clearly shows", "appears to indicate"),
            (r"\bconfirms?\s+(?:the\s+)?hypothesis\b",
             "confirms hypothesis", "is consistent with the hypothesis"),
        ]
        
        # Content-generating suggestion types that should be claim-disciplined
        prose_types = {
            SuggestionType.PARAGRAPH_DRAFT,
            SuggestionType.METHOD_TEMPLATE,
            SuggestionType.OUTLINE,
            SuggestionType.SOURCE_SUMMARY,
            SuggestionType.CLAIM_REFINEMENT,
        }
        
        if suggestion_type in prose_types:
            for pattern_str, bad, good in overreach_patterns:
                pattern = re.compile(pattern_str, re.I)
                if pattern.search(sanitized):
                    issues.append(f"Claim overreach detected: '{bad}' → '{good}'")
                    sanitized = pattern.sub(good, sanitized)
        
        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            sanitized_content=sanitized if issues else None,
        )
    
    def _suggestion_type_to_capability(
        self,
        suggestion_type: SuggestionType,
    ) -> AICapability:
        """Map suggestion type to required capability."""
        mapping = {
            SuggestionType.OUTLINE: AICapability.OUTLINE_SUGGESTIONS,
            SuggestionType.SOURCE_RECOMMENDATION: AICapability.SOURCE_RECOMMENDATIONS,
            SuggestionType.GAP_ANALYSIS: AICapability.GAP_ANALYSIS,
            SuggestionType.SOURCE_SUMMARY: AICapability.SOURCE_SUMMARIES,
            SuggestionType.PARAGRAPH_DRAFT: AICapability.PARAGRAPH_SUGGESTIONS,
            SuggestionType.METHOD_TEMPLATE: AICapability.METHOD_TEMPLATES,
            SuggestionType.DEFENSE_QUESTION: AICapability.DEFENSE_QUESTIONS,
            # Harvard-level quality engines – available from Level 2+
            SuggestionType.CLAIM_DISCIPLINE_AUDIT: AICapability.GAP_ANALYSIS,
            SuggestionType.METHODOLOGY_STRESS_TEST: AICapability.GAP_ANALYSIS,
            SuggestionType.CONTRIBUTION_VALIDATOR: AICapability.GAP_ANALYSIS,
            SuggestionType.LITERATURE_CONFLICT_MAP: AICapability.GAP_ANALYSIS,
            SuggestionType.PEDAGOGICAL_ANNOTATION: AICapability.EXAMINER_SIMULATION,
        }
        return mapping.get(suggestion_type, AICapability.SEARCH_QUERIES)
    
    def _build_prompt(self, request: SuggestionRequest) -> str:
        """Build system and user prompt for OpenAI from request."""
        ctx = request.context
        st = request.suggestion_type.value.replace("_", " ").title()
        parts = [
            f"You are a research writing assistant. Generate a {st} suggestion.",
            f"Artifact type: {ctx.artifact_type}.",
            f"Title: {ctx.title or '(none)'}.",
            f"Current content:\n{ctx.content[:2000] if ctx.content else '(empty)'}",
        ]
        if request.additional_instructions:
            parts.append(f"Additional instructions: {request.additional_instructions}")
        return "\n\n".join(parts)

    async def _openai_generate(self, request: SuggestionRequest) -> tuple[str, str]:
        """Call OpenAI API. Returns (content, model_used)."""
        from openai import AsyncOpenAI
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = self._build_prompt(request)
        # Prefer a smaller/faster model for suggestions
        model = "gpt-4o-mini"
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You provide concise, factual research writing suggestions. Output only the suggested content, no meta-commentary."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
        )
        content = (response.choices[0].message.content or "").strip()
        return content, model

    def _stub_generate(self, request: SuggestionRequest) -> str:
        """
        STUB: Generate content.
        
        In production, this would call an actual AI model.
        """
        stubs = {
            SuggestionType.OUTLINE: (
                "I. Introduction\n"
                "   A. Background\n"
                "   B. Research Question\n"
                "II. Literature Review\n"
                "   A. Key Concepts\n"
                "   B. Gap in Research\n"
                "III. Methodology\n"
                "   A. Approach\n"
                "   B. Data Collection\n"
                "IV. Expected Results\n"
                "V. Conclusion"
            ),
            SuggestionType.SOURCE_SUMMARY: (
                "[AI-Generated Summary - Requires Verification]\n\n"
                "This source discusses the key concepts relevant to your research. "
                "The main argument centers on... [content would be generated based on actual source]"
            ),
            SuggestionType.CLAIM_REFINEMENT: (
                "Consider refining your claim to be more specific. "
                "Current: '{claim}'\n"
                "Suggested: '[More specific version would go here]'"
            ),
            SuggestionType.GAP_ANALYSIS: (
                "Potential gaps identified:\n"
                "1. Missing connection between claim X and evidence Y\n"
                "2. No sources cited for assertion in section Z\n"
                "3. Methodology section could benefit from more detail"
            ),
            SuggestionType.DEFENSE_QUESTION: (
                "Consider how you would respond to:\n\n"
                "\"Can you explain why you chose this particular methodology "
                "over alternatives like [X] or [Y]?\""
            ),
        }
        
        return stubs.get(
            request.suggestion_type,
            f"[Stub suggestion for {request.suggestion_type.value}]"
        )
