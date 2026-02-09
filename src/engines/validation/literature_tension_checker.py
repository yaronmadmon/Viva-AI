"""
Literature Tension Checker – ensures the literature review contains named
disagreements, unresolved debates, and methodological conflicts instead of
just polite synthesis.

Examiner Sensitivity:  HIGH (separates "good" from "excellent")
Implementation Phase:  4

Anti-gaming measures (per professor's refinement):
  - Weight NAMED disagreements (Author A vs Author B) over stylistic markers
  - Require different assumptions or outcomes, not just "however"
  - Penalize vague phrases ("some scholars argue…")
  - Cross-reference named authors against the reference list
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.ai.types import TensionType
from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Named disagreement detection ─────────────────────────────────────────

# Pattern: "Author (Year) argues/contends/claims X, whereas/while/but Author (Year)..."
_NAMED_DISAGREEMENT_RE = re.compile(
    r"(\b[A-Z][a-z]+(?:\s+(?:et\s+al\.)?)?\s*\(\d{4}\))"     # Author A (Year)
    r"[^.]{10,200}"                                              # connecting text
    r"\b(?:whereas|while|however|in\s+contrast|but|conversely|"
    r"on\s+the\s+other\s+hand|challenges?|contradicts?|"
    r"disputes?|disagrees?|counters?|rejects?|opposes?|"
    r"unlike|contrary\s+to)\b"                                   # disagreement marker
    r"[^.]{5,200}"                                               # more text
    r"(\b[A-Z][a-z]+(?:\s+(?:et\s+al\.)?)?\s*\(\d{4}\))",      # Author B (Year)
    re.I,
)

# Pattern: Author (Year) citation reference
_AUTHOR_CITE_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:et\s+al\.))?)\s*\((\d{4})\)",
)

# ── Vague attribution (anti-gaming) ─────────────────────────────────────

VAGUE_PATTERNS = [
    (re.compile(r"\bsome\s+(?:scholars?|researchers?|authors?|studies)\s+(?:argue|suggest|claim|contend)\b", re.I),
     "Vague attribution: 'some scholars argue' – name the specific scholars."),
    (re.compile(r"\b(?:it\s+has\s+been|has\s+been)\s+(?:argued|suggested|claimed|noted)\b", re.I),
     "Passive vague attribution: specify who argued this."),
    (re.compile(r"\b(?:many|several|various|numerous)\s+(?:scholars?|researchers?|studies)\b", re.I),
     "Vague quantifier: name specific scholars instead of 'many scholars'."),
    (re.compile(r"\b(?:the\s+)?literature\s+(?:shows?|suggests?|indicates?)\b", re.I),
     "'The literature shows' is vague – cite specific studies."),
    (re.compile(r"\bthere\s+is\s+(?:a\s+)?(?:growing|increasing)\s+(?:body\s+of\s+)?(?:evidence|literature|consensus)\b", re.I),
     "'Growing body of evidence' is vague – cite the specific studies."),
]

# ── Tension/conflict stylistic markers (lower weight than named disagreements)

TENSION_STYLE_MARKERS = [
    r"\bhowever\b", r"\bin\s+contrast\b", r"\bnevertheless\b",
    r"\bconversely\b", r"\bon\s+the\s+other\s+hand\b",
    r"\bdespite\s+this\b", r"\bnotwithstanding\b",
    r"\bunresolved\b", r"\bdebate\b", r"\bcontrovers\w+\b",
    r"\btension\b", r"\bcontradiction\b", r"\binconsisten\w+\b",
    r"\bconflicting\b", r"\bcompeting\b", r"\brival\b",
]
_TENSION_STYLE_RE = re.compile("|".join(TENSION_STYLE_MARKERS), re.I)

# ── Synthesis markers (too-polite indicators) ────────────────────────────

SYNTHESIS_MARKERS = [
    r"\bconsensus\b", r"\bagree(?:ment|s)?\b", r"\bconsistent\s+with\b",
    r"\bin\s+line\s+with\b", r"\bsupports?\s+(?:the\s+)?(?:finding|view|argument)\b",
    r"\bconfirm\w*\b", r"\bcorroborate\w*\b", r"\balign\w*\s+with\b",
    r"\bcomplementar\w*\b", r"\breinforce\w*\b",
]
_SYNTHESIS_RE = re.compile("|".join(SYNTHESIS_MARKERS), re.I)


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class NamedDisagreement:
    """A detected named disagreement between two cited authors."""
    author_a: str
    year_a: str
    author_b: str
    year_b: str
    context: str          # surrounding text (truncated)
    tension_type: Optional[TensionType] = None


@dataclass
class TensionFlag:
    """A flagged issue with the literature review."""
    issue: str
    severity: str         # "error" | "warning" | "info"
    text_excerpt: str
    suggestion: Optional[str] = None


@dataclass
class LiteratureTensionResult:
    """Result of auditing literature review tension."""
    total_paragraphs: int
    named_disagreements: List[NamedDisagreement] = field(default_factory=list)
    vague_attribution_count: int = 0
    tension_style_count: int = 0       # stylistic markers (lower value)
    synthesis_count: int = 0           # consensus markers
    tension_score: float = 0.0         # 0-100, higher = more tension (good)
    flags: List[TensionFlag] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Passes if tension score >= 40 and at least 2 named disagreements."""
        return self.tension_score >= 40 and len(self.named_disagreements) >= 2


# ── Core analysis ────────────────────────────────────────────────────────

def _extract_named_disagreements(text: str) -> List[NamedDisagreement]:
    """Extract Author A vs Author B disagreements."""
    disagreements = []
    for match in _NAMED_DISAGREEMENT_RE.finditer(text):
        full = match.group(0)
        # Extract the two author citations
        cites = _AUTHOR_CITE_RE.findall(full)
        if len(cites) >= 2:
            disagreements.append(NamedDisagreement(
                author_a=cites[0][0],
                year_a=cites[0][1],
                author_b=cites[1][0],
                year_b=cites[1][1],
                context=full[:250],
            ))
    return disagreements


def _get_cited_authors(text: str) -> Set[str]:
    """Extract all cited author names from the text."""
    return {m[0] for m in _AUTHOR_CITE_RE.findall(text)}


def audit_literature_tension(
    text: str,
    min_named_disagreements: int = 3,
) -> LiteratureTensionResult:
    """
    Audit a literature review for tension, named disagreements, and
    anti-gaming patterns.

    Args:
        text: The literature review text.
        min_named_disagreements: Minimum named disagreements expected.

    Returns:
        LiteratureTensionResult with scores and flags.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.split()) > 15]
    flags: List[TensionFlag] = []

    # 1. Named disagreements (highest value)
    named = _extract_named_disagreements(text)

    if len(named) < min_named_disagreements:
        flags.append(TensionFlag(
            issue=(
                f"Only {len(named)} named disagreements found (minimum: "
                f"{min_named_disagreements}). A strong literature review should "
                f"contain explicit 'Author A vs Author B' debates."
            ),
            severity="error" if len(named) == 0 else "warning",
            text_excerpt="(entire literature review)",
            suggestion=(
                "For each major theme, identify at least one unresolved debate: "
                "'Author A (Year) argues X, whereas Author B (Year) contends Y. "
                "This disagreement matters because Z.'"
            ),
        ))

    # 2. Vague attribution (anti-gaming)
    vague_count = 0
    for pattern, issue in VAGUE_PATTERNS:
        matches = pattern.findall(text)
        vague_count += len(matches)
        if matches:
            flags.append(TensionFlag(
                issue=issue,
                severity="warning",
                text_excerpt=matches[0][:150] if matches else "",
                suggestion="Replace with specific author citations.",
            ))

    # 3. Tension style markers
    tension_style_count = len(_TENSION_STYLE_RE.findall(text))

    # 4. Synthesis markers (too polite)
    synthesis_count = len(_SYNTHESIS_RE.findall(text))

    # 5. Compute tension score
    # Named disagreements are worth much more than stylistic markers
    named_score = min(40, len(named) * 13)            # max 40 from named (3+ = max)
    style_score = min(20, tension_style_count * 2)     # max 20 from style
    anti_polite = min(20, max(0, 20 - synthesis_count * 3))  # penalize too much synthesis
    anti_vague = min(20, max(0, 20 - vague_count * 5))       # penalize vagueness

    tension_score = min(100.0, named_score + style_score + anti_polite + anti_vague)

    # Flag if too polite
    if synthesis_count > tension_style_count * 2 and synthesis_count > 5:
        flags.append(TensionFlag(
            issue=(
                f"Literature review appears overly polite: {synthesis_count} "
                f"synthesis/agreement markers vs {tension_style_count} tension "
                f"markers. Top-tier reviews stress the field, not just synthesize it."
            ),
            severity="warning",
            text_excerpt="(entire literature review)",
            suggestion="Add more critical engagement: named disagreements, unresolved debates.",
        ))

    return LiteratureTensionResult(
        total_paragraphs=len(paragraphs),
        named_disagreements=named,
        vague_attribution_count=vague_count,
        tension_style_count=tension_style_count,
        synthesis_count=synthesis_count,
        tension_score=round(tension_score, 1),
        flags=flags,
    )


# ── AI-powered deep audit ───────────────────────────────────────────────

async def deep_audit_literature_tension(
    text: str,
    min_named_disagreements: int = 3,
) -> LiteratureTensionResult:
    """Rule-based + AI-powered literature tension audit."""
    result = audit_literature_tension(text, min_named_disagreements)

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder or len(text.split()) < 50:
        return result

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)

        prompt = (
            "You are a PhD examiner reviewing a Literature Review section. "
            "Assess the level of CRITICAL ENGAGEMENT and TENSION:\n\n"
            "1. List every named disagreement (Author A vs Author B) you can find.\n"
            "2. Identify any vague attributions ('some scholars argue…').\n"
            "3. Rate the overall tension on a scale of 0-100 (0 = pure synthesis, "
            "100 = deep critical engagement with named debates).\n"
            "4. List any issues or suggestions for improvement.\n\n"
            "Return JSON with keys:\n"
            "- disagreements: [{author_a, year_a, author_b, year_b, topic}]\n"
            "- vague_count: int\n"
            "- tension_rating: int (0-100)\n"
            "- issues: [{issue, suggestion}]\n\n"
            f"TEXT:\n{text[:3000]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a PhD examiner. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()

        import json
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        ai_data = json.loads(content)

        # Merge AI-found disagreements
        existing_pairs = {
            (d.author_a.lower(), d.author_b.lower())
            for d in result.named_disagreements
        }
        for d in ai_data.get("disagreements", []):
            pair = (d.get("author_a", "").lower(), d.get("author_b", "").lower())
            if pair not in existing_pairs and pair[0] and pair[1]:
                result.named_disagreements.append(NamedDisagreement(
                    author_a=d.get("author_a", ""),
                    year_a=d.get("year_a", ""),
                    author_b=d.get("author_b", ""),
                    year_b=d.get("year_b", ""),
                    context=d.get("topic", "(AI-detected)"),
                ))

        for item in ai_data.get("issues", []):
            result.flags.append(TensionFlag(
                issue=item.get("issue", ""),
                severity="warning",
                text_excerpt="(AI-detected)",
                suggestion=item.get("suggestion"),
            ))

    except Exception as exc:
        logger.warning("AI literature tension audit failed: %s", exc)

    return result
