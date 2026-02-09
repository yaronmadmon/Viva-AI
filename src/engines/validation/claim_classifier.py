"""
Claim Discipline Engine – sentence-level claim classification and certainty
calibration.

Examiner Sensitivity:  HIGHEST
Implementation Phase:  1b

This engine:
  1. Classifies every claim-like sentence as DESCRIPTIVE, INFERENTIAL, or
     SPECULATIVE.
  2. Detects overreach patterns (e.g. "proves", "demonstrates conclusively").
  3. Detects unhedged inferential claims missing softening language.
  4. Produces a per-section certainty calibration score.
  5. Suggests softened rewrites for flagged sentences.

Can run against raw text (rule-based) or through OpenAI for deeper analysis.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.ai.types import ClaimLevel
from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)

# ── Overreach patterns (examiner red-flags) ─────────────────────────────

OVERREACH_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # (compiled regex, issue description, suggested replacement)
    (re.compile(r"\bproves?\b(?! that)", re.I),
     "Unqualified 'prove' – evidence supports, it does not prove",
     "suggests"),
    (re.compile(r"\bdemonstrates?\s+conclusively\b", re.I),
     "'Demonstrates conclusively' overstates certainty",
     "indicates"),
    (re.compile(r"\bestablish(?:es)?\s+beyond\s+doubt\b", re.I),
     "'Establishes beyond doubt' overstates certainty",
     "provides evidence for"),
    (re.compile(r"\bclearly\s+shows?\b", re.I),
     "'Clearly shows' implies uncontested truth",
     "appears to indicate"),
    (re.compile(r"\bundeniab(?:ly|le)\b", re.I),
     "'Undeniable' overstates certainty",
     "notable"),
    (re.compile(r"\b(?:is|are)\s+generalizable?\s+to\s+all\b", re.I),
     "Claiming universal generalizability",
     "may be applicable to similar populations"),
    (re.compile(r"\bwill\s+transform\b", re.I),
     "'Will transform' overstates impact",
     "may contribute to"),
    (re.compile(r"\bready\s+for\s+clinical\s+use\b", re.I),
     "Clinical readiness claim requires regulatory evidence",
     "warrants further investigation for potential clinical application"),
    (re.compile(r"\bconfirms?\s+(?:the\s+)?hypothesis\b", re.I),
     "'Confirms hypothesis' overstates – findings are consistent with",
     "is consistent with the hypothesis"),
    (re.compile(r"\birrefutabl[ey]\b", re.I),
     "'Irrefutable' overstates certainty",
     "substantial"),
    (re.compile(r"\bdefinitively\b", re.I),
     "'Definitively' overstates certainty",
     "substantively"),
    (re.compile(r"\b(?:it\s+is\s+)?certain\s+that\b", re.I),
     "'Certain that' overstates epistemological status",
     "evidence strongly suggests that"),
]

# ── Hedging markers (present = properly scoped inferential claim) ────────

HEDGING_MARKERS = [
    r"\bsuggests?\b", r"\bindicates?\b", r"\bappears?\s+to\b",
    r"\bmay\b", r"\bmight\b", r"\bcould\b", r"\bpossib(?:ly|le)\b",
    r"\btends?\s+to\b", r"\bseems?\s+to\b", r"\bis\s+likely\b",
    r"\bimplies?\b", r"\bwarrants?\b", r"\bfurther\s+research\b",
    r"\bis\s+consistent\s+with\b", r"\bpoints?\s+to\b",
    r"\bcontributes?\s+to\b",
]
_HEDGE_RE = re.compile("|".join(HEDGING_MARKERS), re.I)

# ── Speculative markers ─────────────────────────────────────────────────

SPECULATIVE_MARKERS = [
    r"\bfuture\s+(?:research|work|studies)\b",
    r"\bremains?\s+to\s+be\s+(?:seen|determined|explored)\b",
    r"\bpotentially\b",
    r"\bspeculat(?:e|ive|ion)\b",
    r"\bhypothesiz(?:e|ed)\b",
    r"\bone\s+might\s+expect\b",
    r"\bit\s+is\s+conceivable\b",
    r"\bbeyond\s+the\s+scope\b",
]
_SPECULATIVE_RE = re.compile("|".join(SPECULATIVE_MARKERS), re.I)

# ── Descriptive markers (citation patterns, data reporting) ──────────────

DESCRIPTIVE_MARKERS = [
    r"\(\w+(?:\s+et\s+al\.)?,?\s*\d{4}\)",          # (Author, 2023)
    r"\baccording\s+to\b",
    r"\breported\s+that\b",
    r"\b(?:Table|Figure)\s+\d",
    r"\bN\s*=\s*\d",
    r"\bp\s*[<>=]\s*[\d.]",
    r"\bwas\s+found\s+to\b",
    r"\bthe\s+data\s+show\b",
]
_DESCRIPTIVE_RE = re.compile("|".join(DESCRIPTIVE_MARKERS), re.I)


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class ClaimFlag:
    """One flagged sentence with classification and suggested fix."""
    sentence: str
    level: ClaimLevel
    issue: str
    severity: str              # "error" | "warning" | "info"
    suggestion: Optional[str] = None
    line_hint: int = 0         # approximate line number in section


@dataclass
class ClaimAuditResult:
    """Result of auditing a section / block of text."""
    section_title: str
    total_sentences: int
    descriptive_count: int
    inferential_count: int
    speculative_count: int
    overreach_count: int
    unhedged_inferential_count: int
    certainty_score: float            # 0-100, lower = more cautious (good)
    flags: List[ClaimFlag] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Passes if no errors and certainty score < 40."""
        errors = [f for f in self.flags if f.severity == "error"]
        return len(errors) == 0 and self.certainty_score < 40


# ── Rule-based classifier ───────────────────────────────────────────────

def _split_sentences(text: str) -> List[str]:
    """Naive sentence splitter that handles common academic patterns."""
    # Split on period/question/exclamation followed by space+uppercase or end
    raw = re.split(r'(?<=[.?!])\s+(?=[A-Z"\'])', text)
    return [s.strip() for s in raw if s.strip() and len(s.split()) >= 4]


def _classify_sentence(sentence: str) -> ClaimLevel:
    """Classify a single sentence using regex heuristics."""
    has_desc = bool(_DESCRIPTIVE_RE.search(sentence))
    has_spec = bool(_SPECULATIVE_RE.search(sentence))
    has_hedge = bool(_HEDGE_RE.search(sentence))

    # Descriptive if it contains citation/data patterns and no speculation
    if has_desc and not has_spec:
        return ClaimLevel.DESCRIPTIVE

    # Speculative if it contains speculative markers
    if has_spec:
        return ClaimLevel.SPECULATIVE

    # Otherwise inferential (the default for academic prose)
    return ClaimLevel.INFERENTIAL


def audit_section(text: str, section_title: str = "") -> ClaimAuditResult:
    """
    Audit a block of academic text for claim discipline issues.

    Returns a ClaimAuditResult with per-sentence classifications,
    overreach flags, and a certainty calibration score.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return ClaimAuditResult(
            section_title=section_title,
            total_sentences=0,
            descriptive_count=0,
            inferential_count=0,
            speculative_count=0,
            overreach_count=0,
            unhedged_inferential_count=0,
            certainty_score=0.0,
            flags=[],
        )

    counts: Dict[ClaimLevel, int] = {
        ClaimLevel.DESCRIPTIVE: 0,
        ClaimLevel.INFERENTIAL: 0,
        ClaimLevel.SPECULATIVE: 0,
    }
    flags: List[ClaimFlag] = []
    overreach_count = 0
    unhedged_count = 0

    for i, sent in enumerate(sentences):
        level = _classify_sentence(sent)
        counts[level] += 1

        # Check for overreach patterns
        for pattern, issue, replacement in OVERREACH_PATTERNS:
            if pattern.search(sent):
                overreach_count += 1
                match = pattern.search(sent)
                original_word = match.group(0) if match else ""
                suggested = sent
                if match:
                    suggested = sent[:match.start()] + replacement + sent[match.end():]
                flags.append(ClaimFlag(
                    sentence=sent[:200],
                    level=level,
                    issue=issue,
                    severity="error",
                    suggestion=suggested[:200],
                    line_hint=i + 1,
                ))

        # Check for unhedged inferential claims
        if level == ClaimLevel.INFERENTIAL and not _HEDGE_RE.search(sent):
            # Only flag if the sentence makes a strong claim
            strong_claim_markers = re.compile(
                r"\b(?:is|are|was|were|has|have|shows?|reveals?|demonstrates?)\b",
                re.I,
            )
            if strong_claim_markers.search(sent):
                unhedged_count += 1
                flags.append(ClaimFlag(
                    sentence=sent[:200],
                    level=ClaimLevel.INFERENTIAL,
                    issue="Inferential claim lacks hedging language",
                    severity="warning",
                    suggestion=None,
                    line_hint=i + 1,
                ))

    total = len(sentences)
    # Certainty score: higher = more overreach (bad)
    # Based on: overreach errors + unhedged inferential ratio
    overreach_ratio = overreach_count / total if total else 0
    unhedged_ratio = unhedged_count / max(counts[ClaimLevel.INFERENTIAL], 1)
    certainty_score = min(100.0, (overreach_ratio * 60 + unhedged_ratio * 40) * 100)

    return ClaimAuditResult(
        section_title=section_title,
        total_sentences=total,
        descriptive_count=counts[ClaimLevel.DESCRIPTIVE],
        inferential_count=counts[ClaimLevel.INFERENTIAL],
        speculative_count=counts[ClaimLevel.SPECULATIVE],
        overreach_count=overreach_count,
        unhedged_inferential_count=unhedged_count,
        certainty_score=round(certainty_score, 1),
        flags=flags,
    )


# ── AI-powered deep audit (uses OpenAI when available) ──────────────────

async def deep_audit_section(text: str, section_title: str = "") -> ClaimAuditResult:
    """
    Run both rule-based and AI-powered audit.

    Falls back to rule-based only if OpenAI is unavailable.
    The AI pass catches nuanced overreach that regex misses.
    """
    # Always start with rule-based
    result = audit_section(text, section_title)

    # Attempt AI-powered pass for deeper analysis
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder or len(text.split()) < 20:
        return result

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)

        # Use gpt-4o for validation passes (higher-stakes, lower-volume)
        prompt = (
            "You are an examiner at a top-tier university reviewing a PhD "
            "dissertation section. Analyze the following text for CLAIM "
            "DISCIPLINE issues.\n\n"
            "For each problematic sentence, provide:\n"
            "- The sentence (first 150 chars)\n"
            "- Classification: DESCRIPTIVE / INFERENTIAL / SPECULATIVE\n"
            "- Issue: what's wrong\n"
            "- Suggested rewrite\n\n"
            "Focus on:\n"
            "1. Claims that overstate certainty (e.g. 'proves', 'conclusively')\n"
            "2. Inferential claims lacking hedging language\n"
            "3. Speculative claims presented as established fact\n"
            "4. Generalizability claims without scope limitation\n"
            "5. Clinical/practical readiness claims without evidence\n\n"
            "Return ONLY a JSON array of objects with keys: "
            "sentence, level, issue, suggestion\n"
            "If no issues found, return []\n\n"
            f"TEXT:\n{text[:3000]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an academic examiner. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()

        # Parse AI response and merge with rule-based results
        import json
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        ai_flags = json.loads(content)

        existing_sents = {f.sentence[:80] for f in result.flags}
        for item in ai_flags:
            sent_preview = (item.get("sentence") or "")[:200]
            if sent_preview[:80] not in existing_sents:
                level_str = (item.get("level") or "inferential").lower()
                level_map = {
                    "descriptive": ClaimLevel.DESCRIPTIVE,
                    "inferential": ClaimLevel.INFERENTIAL,
                    "speculative": ClaimLevel.SPECULATIVE,
                }
                result.flags.append(ClaimFlag(
                    sentence=sent_preview,
                    level=level_map.get(level_str, ClaimLevel.INFERENTIAL),
                    issue=item.get("issue", "AI-detected claim discipline issue"),
                    severity="warning",
                    suggestion=item.get("suggestion"),
                ))

    except Exception as exc:
        logger.warning("AI claim audit failed, using rule-based only: %s", exc)

    return result
