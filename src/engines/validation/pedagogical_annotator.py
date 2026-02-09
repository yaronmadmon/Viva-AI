"""
Pedagogical Meta-Commentary Annotator – generates "why this exists"
explanations for each paragraph and structural move in a dissertation section.

Examiner Sensitivity:  MEDIUM-HIGH (transforms Viva into a teaching system)
Implementation Phase:  6

This engine:
  1. Analyzes the structure of a dissertation section.
  2. For each paragraph or structural move, generates an annotation
     explaining the academic reasoning behind it.
  3. Annotations are stored alongside artifacts and are OPTIONAL by default
     (toggled on for teaching/supervisor review mode).

Annotation types:
  - STRUCTURAL: "This paragraph exists to establish the research gap."
  - DEFENSIVE:  "This section prevents examiner criticism about X."
  - RHETORICAL: "This transition signals a shift from synthesis to critique."
  - CLAIM:      "This is an inferential claim that requires hedging."
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Annotation types ─────────────────────────────────────────────────────

class AnnotationType:
    STRUCTURAL = "structural"
    DEFENSIVE = "defensive"
    RHETORICAL = "rhetorical"
    CLAIM = "claim"


@dataclass
class PedagogicalAnnotation:
    """One annotation attached to a text range within a section."""
    id: str
    annotation_type: str               # AnnotationType values
    paragraph_index: int                # 0-based paragraph number
    explanation: str                    # "This paragraph exists to..."
    examiner_concern: Optional[str] = None  # "Prevents criticism about..."
    created_at: Optional[datetime] = None


@dataclass
class AnnotatedSection:
    """A section with pedagogical annotations attached."""
    section_title: str
    total_paragraphs: int
    annotations: List[PedagogicalAnnotation] = field(default_factory=list)
    model_used: str = "rule-based"


# ── Rule-based structural patterns ──────────────────────────────────────

_STRUCTURAL_PATTERNS = [
    # (pattern in paragraph text, annotation, type)
    (re.compile(r"^\s*(?:this\s+)?(?:chapter|section|paper|dissertation|study)\s+"
                r"(?:examines?|investigates?|explores?|addresses?|focuses)\b", re.I),
     "Opens the section by stating its purpose – orients the reader.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\bgap\s+in\s+(?:the\s+)?(?:literature|research|knowledge)\b", re.I),
     "Identifies the research gap – justifies the need for this study.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\b(?:however|nevertheless|in\s+contrast|on\s+the\s+other\s+hand)\b", re.I),
     "Introduces tension or counterpoint – signals critical engagement.",
     AnnotationType.RHETORICAL),

    (re.compile(r"\b(?:this|the\s+present)\s+study\s+(?:aims?|seeks?|proposes?|argues?)\b", re.I),
     "States the contribution or argument – the core claim of this section.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\blimitation\w*\b", re.I),
     "Acknowledges limitations – prevents examiner criticism about honesty/scope.",
     AnnotationType.DEFENSIVE),

    (re.compile(r"\b(?:future\s+(?:research|work|studies)|further\s+investigation)\b", re.I),
     "Suggests future research – shows awareness of what remains unanswered.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\b(?:Author|(?:[A-Z][a-z]+)\s+(?:et\s+al\.)?)\s*\(\d{4}\)\s+"
                r"(?:argued?|found|showed?|demonstrated?|reported|suggested?)\b", re.I),
     "Cites specific prior work – grounds the argument in existing literature.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\b(?:rejected?|not\s+(?:chosen|adopted)|rather\s+than)\b", re.I),
     "Names a rejected alternative – strengthens methodological defense.",
     AnnotationType.DEFENSIVE),

    (re.compile(r"\b(?:if\s+this\s+(?:fails?|breaks?)|threat\w*\s+to\s+validity)\b", re.I),
     "States failure conditions – anticipates examiner challenge about validity.",
     AnnotationType.DEFENSIVE),

    (re.compile(r"\b(?:before\s+this\s+(?:work|dissertation|study))\b", re.I),
     "Uses 'before this work' framing – the gold-standard contribution format.",
     AnnotationType.STRUCTURAL),

    (re.compile(r"\b(?:suggests?|indicates?|appears?\s+to|may)\b", re.I),
     "Uses hedging language – properly scopes an inferential claim.",
     AnnotationType.CLAIM),
]


# ── Core annotator ───────────────────────────────────────────────────────

def annotate_section_rule_based(
    text: str,
    section_title: str = "",
) -> AnnotatedSection:
    """
    Generate pedagogical annotations for a section using rule-based
    pattern matching.

    Returns an AnnotatedSection with annotations for each paragraph
    where a structural/defensive/rhetorical pattern is detected.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.split()) > 8]
    annotations: List[PedagogicalAnnotation] = []

    for i, para in enumerate(paragraphs):
        for pattern, explanation, ann_type in _STRUCTURAL_PATTERNS:
            if pattern.search(para):
                annotations.append(PedagogicalAnnotation(
                    id=str(uuid.uuid4())[:8],
                    annotation_type=ann_type,
                    paragraph_index=i,
                    explanation=explanation,
                    created_at=datetime.utcnow(),
                ))
                break  # One annotation per paragraph to avoid noise

    return AnnotatedSection(
        section_title=section_title,
        total_paragraphs=len(paragraphs),
        annotations=annotations,
        model_used="rule-based",
    )


# ── AI-powered deep annotator ───────────────────────────────────────────

async def annotate_section_deep(
    text: str,
    section_title: str = "",
) -> AnnotatedSection:
    """
    Generate rich pedagogical annotations using AI.

    Falls back to rule-based if OpenAI unavailable.
    """
    # Start with rule-based
    result = annotate_section_rule_based(text, section_title)

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder or len(text.split()) < 30:
        return result

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.split()) > 8]
        # Send first 10 paragraphs for annotation
        para_text = "\n\n---\n\n".join(
            f"[Paragraph {i}] {p[:300]}"
            for i, p in enumerate(paragraphs[:10])
        )

        prompt = (
            "You are a PhD supervisor explaining to a student WHY each "
            "paragraph in their dissertation exists. For each paragraph below, "
            "provide:\n"
            "1. A one-sentence explanation of its PURPOSE (why it exists)\n"
            "2. What examiner criticism it prevents (if applicable)\n"
            "3. Classification: STRUCTURAL / DEFENSIVE / RHETORICAL / CLAIM\n\n"
            "Return JSON array: [{paragraph_index, type, explanation, "
            "examiner_concern}]\n\n"
            f"SECTION: {section_title}\n\n"
            f"PARAGRAPHS:\n{para_text}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a PhD supervisor. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        content = (response.choices[0].message.content or "").strip()

        import json
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        ai_data = json.loads(content)

        # Replace rule-based annotations with richer AI ones
        existing_indices = {a.paragraph_index for a in result.annotations}
        for item in ai_data:
            idx = item.get("paragraph_index", -1)
            if idx not in existing_indices and 0 <= idx < len(paragraphs):
                result.annotations.append(PedagogicalAnnotation(
                    id=str(uuid.uuid4())[:8],
                    annotation_type=item.get("type", AnnotationType.STRUCTURAL).lower(),
                    paragraph_index=idx,
                    explanation=item.get("explanation", ""),
                    examiner_concern=item.get("examiner_concern"),
                    created_at=datetime.utcnow(),
                ))

        result.model_used = "gpt-4o-mini"

    except Exception as exc:
        logger.warning("AI pedagogical annotation failed: %s", exc)

    return result
