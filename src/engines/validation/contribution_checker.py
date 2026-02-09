"""
Contribution Validator – ensures the dissertation's contribution is
surgically precise, falsifiable, and framed as "before vs after".

Examiner Sensitivity:  HIGH
Implementation Phase:  3

Checks:
  1. Number of distinct core claims (rejects >2)
  2. "Before vs after" framing present
  3. Falsifiability markers
  4. Rejects overly broad contributions
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Broad-contribution red flags ─────────────────────────────────────────

BROAD_CONTRIBUTION_PATTERNS = [
    (re.compile(r"\bappl(?:y|ies|ied|ying)\b.*\bmethods?\b", re.I),
     "Too broad: 'applying methods' is not a contribution — what specific result does the application produce?"),
    (re.compile(r"\bcompar(?:e|es|ed|ing)\b.*\band\b.*\b(?:models?|approaches)\b", re.I),
     "Comparing approaches is methodology, not contribution — what did the comparison reveal?"),
    (re.compile(r"\bcontributes?\s+to\s+the\s+(?:body\s+of\s+)?(?:knowledge|literature|field)\b", re.I),
     "'Contributes to the body of knowledge' is too vague — specify the exact claim."),
    (re.compile(r"\badvances?\s+(?:the|our)\s+understanding\b", re.I),
     "'Advances understanding' is too broad — what specifically is now understood differently?"),
    (re.compile(r"\bfills?\s+(?:a|the)\s+gap\b", re.I),
     "'Fills a gap' is insufficient — state what was unknown and what is now known."),
    (re.compile(r"\bprovides?\s+(?:new\s+)?insights?\b", re.I),
     "'Provides insights' is too vague — what is the specific, falsifiable insight?"),
    (re.compile(r"\bexplores?\b.*\b(?:relationship|impact|effect)\b", re.I),
     "'Explores the relationship' is a research activity, not a contribution. State the finding."),
]

# ── "Before vs after" markers (gold standard) ───────────────────────────

BEFORE_AFTER_PATTERNS = [
    re.compile(r"\bbefore\s+this\s+(?:dissertation|work|study|research)\b", re.I),
    re.compile(r"\bprior\s+to\s+this\s+(?:work|study|analysis)\b", re.I),
    re.compile(r"\bpreviously\s+(?:assumed|unknown|unclear|unexamined)\b", re.I),
    re.compile(r"\bwas\s+(?:assumed|unknown|unclear|unexamined|unexplored)\b", re.I),
    re.compile(r"\bthis\s+(?:work|dissertation|study)\s+shows\b", re.I),
    re.compile(r"\bthis\s+(?:work|dissertation|study)\s+demonstrates\b", re.I),
    re.compile(r"\bnow\s+we\s+know\b", re.I),
    re.compile(r"\bwe\s+can\s+now\s+(?:see|understand|conclude)\b", re.I),
    re.compile(r"\bchanges?\s+(?:how|what)\s+we\b", re.I),
]

# ── Falsifiability markers ──────────────────────────────────────────────

FALSIFIABILITY_PATTERNS = [
    re.compile(r"\bif\s+.*\bthen\b", re.I),
    re.compile(r"\bfails?\s+(?:when|because|if|under)\b", re.I),
    re.compile(r"\bwould\s+be\s+(?:falsified|disproven|undermined)\b", re.I),
    re.compile(r"\bunder\s+(?:conditions?|circumstances?)\b", re.I),
    re.compile(r"\blimits?\s+of\s+(?:validity|applicability)\b", re.I),
    re.compile(r"\b(?:only|specifically)\s+(?:when|where|for|in)\b", re.I),
    re.compile(r"\bcannot\s+be\s+applied\s+(?:to|when|beyond)\b", re.I),
    re.compile(r"\b(?:does|do)\s+not\s+(?:hold|apply|extend)\b", re.I),
]


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class ContributionFlag:
    """One flagged issue with the contribution statement."""
    issue: str
    severity: str        # "error" | "warning"
    text_excerpt: str    # the problematic text
    suggestion: Optional[str] = None


@dataclass
class ContributionAuditResult:
    """Result of auditing the contribution statement(s)."""
    claim_count: int                  # number of distinct core claims detected
    has_before_after: bool            # "before vs after" framing present
    has_falsifiability: bool          # falsifiability markers present
    broad_claim_count: int            # number of overly broad claims
    precision_score: float            # 0-100, higher = more precise (good)
    flags: List[ContributionFlag] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        errors = [f for f in self.flags if f.severity == "error"]
        return len(errors) == 0 and self.precision_score >= 60


# ── Core analysis ────────────────────────────────────────────────────────

def _count_claims(text: str) -> int:
    """Estimate the number of distinct contribution claims."""
    # Look for numbered claims, "First,...  Second,..." patterns, or
    # sentences starting with "This dissertation shows/demonstrates"
    claim_starters = re.findall(
        r"(?:^|\n)\s*(?:\d+[.)]\s*|(?:First|Second|Third|Fourth|Fifth|"
        r"Additionally|Furthermore|Moreover)[,:]?\s+)?"
        r"(?:This\s+(?:dissertation|work|study|research|thesis)\s+"
        r"(?:shows?|demonstrates?|reveals?|finds?|argues?|establishes?|"
        r"contributes?))",
        text,
        re.I | re.M,
    )
    if claim_starters:
        return len(claim_starters)

    # Fallback: count sentences with strong claim markers in conclusion-like text
    sentences = re.split(r'(?<=[.?!])\s+(?=[A-Z])', text)
    claim_sents = [
        s for s in sentences
        if re.search(
            r"\b(?:contribution|novel|original|new|first|unique)\b",
            s, re.I,
        )
    ]
    return max(1, len(claim_sents))


def audit_contribution(text: str) -> ContributionAuditResult:
    """
    Audit a conclusion or contribution statement for precision.

    Args:
        text: The conclusion section or explicit contribution statement.

    Returns:
        ContributionAuditResult with scores and flags.
    """
    flags: List[ContributionFlag] = []

    # 1. Count claims
    claim_count = _count_claims(text)
    if claim_count > 2:
        flags.append(ContributionFlag(
            issue=(
                f"Too many core claims ({claim_count}). A precise contribution "
                "should have exactly 1-2 irreducible claims. Reduce and sharpen."
            ),
            severity="error",
            text_excerpt=text[:200],
            suggestion="Identify the single most important finding and frame it as your primary contribution.",
        ))

    # 2. Check for "before vs after" framing
    has_before_after = any(p.search(text) for p in BEFORE_AFTER_PATTERNS)
    if not has_before_after:
        flags.append(ContributionFlag(
            issue=(
                "Missing 'before vs after' framing. A strong contribution should "
                "state: 'Before this dissertation, X was assumed. This work shows Y.'"
            ),
            severity="warning",
            text_excerpt=text[:200],
            suggestion=(
                "Add framing like: 'Prior to this work, X was assumed/unknown. "
                "This dissertation shows Y, which means Z.'"
            ),
        ))

    # 3. Check for falsifiability
    has_falsifiability = any(p.search(text) for p in FALSIFIABILITY_PATTERNS)
    if not has_falsifiability:
        flags.append(ContributionFlag(
            issue=(
                "Contribution lacks falsifiability or scope boundaries. "
                "State under what conditions the contribution would NOT hold."
            ),
            severity="warning",
            text_excerpt=text[:200],
            suggestion="Add: 'This finding applies specifically when X. It does not extend to Y.'",
        ))

    # 4. Check for broad claims
    broad_count = 0
    for pattern, issue in BROAD_CONTRIBUTION_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            broad_count += len(matches)
            flags.append(ContributionFlag(
                issue=issue,
                severity="error",
                text_excerpt=matches[0] if isinstance(matches[0], str) else str(matches[0]),
            ))

    # Precision score: 100 = perfect, 0 = very imprecise
    score = 100.0
    # Penalize: too many claims
    if claim_count > 2:
        score -= (claim_count - 2) * 15
    # Reward: before/after framing
    if not has_before_after:
        score -= 20
    # Reward: falsifiability
    if not has_falsifiability:
        score -= 15
    # Penalize: broad claims
    score -= broad_count * 10
    # Penalize: no claims at all
    if claim_count == 0:
        score -= 30

    precision_score = max(0.0, min(100.0, score))

    return ContributionAuditResult(
        claim_count=claim_count,
        has_before_after=has_before_after,
        has_falsifiability=has_falsifiability,
        broad_claim_count=broad_count,
        precision_score=round(precision_score, 1),
        flags=flags,
    )


# ── AI-powered deep audit ───────────────────────────────────────────────

async def deep_audit_contribution(text: str) -> ContributionAuditResult:
    """
    Rule-based + AI-powered contribution audit.
    Falls back to rule-based only if OpenAI unavailable.
    """
    result = audit_contribution(text)

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder or len(text.split()) < 30:
        return result

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)

        prompt = (
            "You are a PhD examiner evaluating the CONTRIBUTION statement of "
            "a dissertation conclusion. Analyze the following text and assess:\n\n"
            "1. How many distinct core claims does the author make? (ideal: 1-2)\n"
            "2. Is there a 'before vs after' framing? (e.g., 'Before this work... "
            "after this work...')\n"
            "3. Is the contribution falsifiable? Could someone disagree with it?\n"
            "4. Is the contribution specific enough, or is it too broad?\n\n"
            "Return a JSON object with keys:\n"
            "- claim_count: int\n"
            "- has_before_after: bool\n"
            "- has_falsifiability: bool\n"
            "- issues: list of {issue: str, severity: 'error'|'warning', suggestion: str}\n\n"
            f"TEXT:\n{text[:2000]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a PhD examiner. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()

        import json
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        ai_data = json.loads(content)

        # Merge AI findings
        for item in ai_data.get("issues", []):
            existing_issues = {f.issue[:60] for f in result.flags}
            issue_text = item.get("issue", "")
            if issue_text[:60] not in existing_issues:
                result.flags.append(ContributionFlag(
                    issue=issue_text,
                    severity=item.get("severity", "warning"),
                    text_excerpt="(AI-detected)",
                    suggestion=item.get("suggestion"),
                ))

    except Exception as exc:
        logger.warning("AI contribution audit failed: %s", exc)

    return result
