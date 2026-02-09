"""
Methodology Stress Test – validates that the methodology section reads as a
defensive argument, not just a procedure description.

Examiner Sensitivity:  HIGH (most common viva failure point)
Implementation Phase:  2

Checks:
  1. Rejected alternatives are named
  2. Failure conditions are stated
  3. Boundary conditions are explicit
  4. Design justification is present (not just description)
  5. Generates examiner-style attack questions during writing
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Defensive methodology markers ────────────────────────────────────────

# Rejected alternatives
REJECTION_PATTERNS = [
    re.compile(r"\b(?:rejected?|not\s+(?:chosen|selected|adopted|used)|"
               r"ruled\s+out|discarded|considered\s+but)\b", re.I),
    re.compile(r"\balternative\w*\s+(?:approach|design|method|technique)\w*\s+"
               r"(?:was|were)\s+(?:considered|evaluated|assessed)\b", re.I),
    re.compile(r"\binstead\s+of\s+(?:using|employing|adopting)\b", re.I),
    re.compile(r"\brather\s+than\b", re.I),
    re.compile(r"\bwas\s+(?:rejected|dismissed)\s+because\b", re.I),
]

# Failure conditions
FAILURE_PATTERNS = [
    re.compile(r"\b(?:if\s+this\s+(?:method|approach|design)\s+fails?)\b", re.I),
    re.compile(r"\bthreat\w*\s+to\s+(?:internal|external|construct)\s+validity\b", re.I),
    re.compile(r"\bfailure\s+condition\w*\b", re.I),
    re.compile(r"\bwould\s+(?:fail|break|invalidate|undermine)\b", re.I),
    re.compile(r"\bweakness\w*\s+(?:of|in)\s+(?:this|the)\s+(?:design|approach|method)\b", re.I),
    re.compile(r"\b(?:risks?\s+(?:of|to)|vulnerabilit\w+)\b", re.I),
    re.compile(r"\blimitation\w*\s+(?:of|in)\s+(?:the\s+)?(?:design|approach|method)\b", re.I),
]

# Boundary conditions
BOUNDARY_PATTERNS = [
    re.compile(r"\bboundary\s+condition\w*\b", re.I),
    re.compile(r"\b(?:valid|applicable|generalizable)\s+(?:only\s+)?(?:for|within|when|to)\b", re.I),
    re.compile(r"\bdoes?\s+not\s+(?:apply|extend|generalize|hold)\b", re.I),
    re.compile(r"\bscope\s+(?:of\s+)?(?:validity|applicability|findings)\b", re.I),
    re.compile(r"\b(?:excluded|beyond\s+the\s+scope)\b", re.I),
    re.compile(r"\b(?:specifically|only)\s+(?:designed\s+)?(?:for|to|within)\b", re.I),
    re.compile(r"\bdelimitation\w*\b", re.I),
]

# Design justification (not just description)
JUSTIFICATION_PATTERNS = [
    re.compile(r"\b(?:justified?\s+(?:by|because)|justification\s+for)\b", re.I),
    re.compile(r"\b(?:chosen|selected|adopted)\s+because\b", re.I),
    re.compile(r"\bthe\s+reason\s+for\s+(?:choosing|selecting|adopting|using)\b", re.I),
    re.compile(r"\bappropriate\s+(?:because|for\s+this|given)\b", re.I),
    re.compile(r"\b(?:this|the)\s+(?:design|approach|method)\s+(?:is|was)\s+"
               r"(?:suitable|appropriate|well-suited|best\s+suited)\b", re.I),
    re.compile(r"\benables?\s+(?:us\s+)?to\b", re.I),
]

# Procedural-only markers (description without argument)
PROCEDURAL_PATTERNS = [
    re.compile(r"\bdata\s+(?:was|were)\s+collected\b", re.I),
    re.compile(r"\bparticipants?\s+(?:was|were)\s+(?:selected|recruited|sampled)\b", re.I),
    re.compile(r"\b(?:we|the\s+researcher)\s+(?:used|employed|utilized|conducted)\b", re.I),
    re.compile(r"\bthe\s+(?:survey|questionnaire|instrument)\s+(?:was|were)\s+"
               r"(?:administered|distributed|sent)\b", re.I),
]


# ── Data models ──────────────────────────────────────────────────────────

@dataclass
class StressTestFlag:
    """One flagged issue with the methodology."""
    issue: str
    severity: str         # "error" | "warning"
    category: str         # "rejection" | "failure" | "boundary" | "justification" | "procedural"
    suggestion: Optional[str] = None


@dataclass
class ExaminerQuestion:
    """A generated examiner-style attack question."""
    question: str
    category: str         # "design" | "validity" | "generalizability" | "alternatives"
    expected_elements: List[str] = field(default_factory=list)


@dataclass
class MethodologyStressResult:
    """Result of stress-testing the methodology section."""
    has_rejected_alternatives: bool
    has_failure_conditions: bool
    has_boundary_conditions: bool
    has_justification: bool
    procedural_ratio: float           # % of text that's procedural vs argumentative
    defensibility_score: float        # 0-100, higher = more defensible (good)
    examiner_questions: List[ExaminerQuestion] = field(default_factory=list)
    flags: List[StressTestFlag] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        errors = [f for f in self.flags if f.severity == "error"]
        return len(errors) == 0 and self.defensibility_score >= 50


# ── Core analysis ────────────────────────────────────────────────────────

def _count_pattern_matches(text: str, patterns: list) -> int:
    return sum(len(p.findall(text)) for p in patterns)


def stress_test_methodology(text: str) -> MethodologyStressResult:
    """
    Stress-test a methodology section for defensibility.

    Returns a MethodologyStressResult with scores, flags, and examiner
    questions that the methodology should be able to answer.
    """
    flags: List[StressTestFlag] = []
    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]
    total_sents = max(1, len(sentences))

    # 1. Rejected alternatives
    rejection_count = _count_pattern_matches(text, REJECTION_PATTERNS)
    has_rejections = rejection_count >= 2  # Need at least 2 named rejections
    if not has_rejections:
        flags.append(StressTestFlag(
            issue=(
                f"Only {rejection_count} rejected alternative(s) found. "
                "A defensible methodology must name at least 2-3 alternative "
                "approaches that were considered and rejected, with reasons."
            ),
            severity="error" if rejection_count == 0 else "warning",
            category="rejection",
            suggestion=(
                "Add: 'Alternative approach X was considered but rejected because Y. "
                "Specifically, [design/method] was not suitable due to Z.'"
            ),
        ))

    # 2. Failure conditions
    failure_count = _count_pattern_matches(text, FAILURE_PATTERNS)
    has_failure = failure_count >= 1
    if not has_failure:
        flags.append(StressTestFlag(
            issue=(
                "No failure conditions stated. A defensible methodology must "
                "include: 'If this methodology fails, it fails because…'"
            ),
            severity="error",
            category="failure",
            suggestion=(
                "Add a subsection: 'Threats to Validity and Failure Conditions' "
                "covering internal validity threats, external validity boundaries, "
                "and construct validity concerns."
            ),
        ))

    # 3. Boundary conditions
    boundary_count = _count_pattern_matches(text, BOUNDARY_PATTERNS)
    has_boundaries = boundary_count >= 1
    if not has_boundaries:
        flags.append(StressTestFlag(
            issue=(
                "No boundary conditions specified. State the exact scope within "
                "which findings are valid (populations, contexts, timeframes "
                "that are explicitly excluded)."
            ),
            severity="error",
            category="boundary",
            suggestion=(
                "Add: 'These findings are valid specifically for [population/context]. "
                "They do not extend to [excluded populations/contexts/timeframes].'"
            ),
        ))

    # 4. Design justification
    justification_count = _count_pattern_matches(text, JUSTIFICATION_PATTERNS)
    has_justification = justification_count >= 2
    if not has_justification:
        flags.append(StressTestFlag(
            issue=(
                "Insufficient design justification. The methodology reads more "
                "as procedure description than as a defensive argument."
            ),
            severity="warning",
            category="justification",
            suggestion=(
                "For each methodological choice, add: 'This approach was chosen "
                "because X. It is appropriate for this study because Y.'"
            ),
        ))

    # 5. Procedural ratio
    procedural_count = _count_pattern_matches(text, PROCEDURAL_PATTERNS)
    argument_count = justification_count + rejection_count + failure_count + boundary_count
    total_markers = max(1, procedural_count + argument_count)
    procedural_ratio = procedural_count / total_markers

    if procedural_ratio > 0.7:
        flags.append(StressTestFlag(
            issue=(
                f"Methodology is {procedural_ratio:.0%} procedural vs "
                f"{1-procedural_ratio:.0%} argumentative. It reads as a "
                "description, not a defensive argument."
            ),
            severity="warning",
            category="procedural",
            suggestion="Convert descriptions into justified choices.",
        ))

    # Defensibility score
    score = 0.0
    if has_rejections:
        score += 25
    elif rejection_count == 1:
        score += 12
    if has_failure:
        score += 25
    if has_boundaries:
        score += 25
    if has_justification:
        score += 15
    elif justification_count >= 1:
        score += 8
    # Bonus for low procedural ratio
    if procedural_ratio < 0.5:
        score += 10

    # Default examiner questions (generated from what's missing)
    examiner_questions = _generate_examiner_questions(
        has_rejections, has_failure, has_boundaries, has_justification
    )

    return MethodologyStressResult(
        has_rejected_alternatives=has_rejections,
        has_failure_conditions=has_failure,
        has_boundary_conditions=has_boundaries,
        has_justification=has_justification,
        procedural_ratio=round(procedural_ratio, 2),
        defensibility_score=min(100.0, round(score, 1)),
        examiner_questions=examiner_questions,
        flags=flags,
    )


def _generate_examiner_questions(
    has_rejections: bool,
    has_failure: bool,
    has_boundaries: bool,
    has_justification: bool,
) -> List[ExaminerQuestion]:
    """Generate examiner-style attack questions based on what's missing."""
    questions = []

    if not has_rejections:
        questions.append(ExaminerQuestion(
            question="Why exactly this design — and what alternatives did you consider?",
            category="alternatives",
            expected_elements=["named_alternatives", "rejection_reasons", "comparison"],
        ))

    if not has_failure:
        questions.append(ExaminerQuestion(
            question="Under what conditions would your methodology produce invalid results?",
            category="validity",
            expected_elements=["internal_threats", "external_threats", "construct_threats"],
        ))

    if not has_boundaries:
        questions.append(ExaminerQuestion(
            question="To what extent can your findings be generalized beyond this specific study?",
            category="generalizability",
            expected_elements=["population_scope", "context_scope", "temporal_scope"],
        ))

    if not has_justification:
        questions.append(ExaminerQuestion(
            question="Why is this particular methodology the best fit for your research question?",
            category="design",
            expected_elements=["fit_argument", "strengths", "limitations_acknowledged"],
        ))

    # Always ask
    questions.append(ExaminerQuestion(
        question="What would break your study? What is the single weakest methodological choice?",
        category="validity",
        expected_elements=["weakest_link", "mitigation", "impact_on_findings"],
    ))

    return questions


# ── AI-powered deep stress test ──────────────────────────────────────────

async def deep_stress_test_methodology(text: str) -> MethodologyStressResult:
    """Rule-based + AI-powered methodology stress test."""
    result = stress_test_methodology(text)

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder or len(text.split()) < 50:
        return result

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)

        prompt = (
            "You are a PhD examiner about to conduct a viva. Read the following "
            "Methodology section and generate 3-5 challenging examiner questions "
            "that would expose weaknesses in the methodological argument.\n\n"
            "Focus on:\n"
            "1. Design choices that aren't justified\n"
            "2. Missing alternative approaches\n"
            "3. Threats to validity not addressed\n"
            "4. Generalizability claims without bounds\n"
            "5. Assumptions that aren't stated\n\n"
            "Return JSON: {questions: [{question, category, weakness_exploited}]}\n\n"
            f"TEXT:\n{text[:3000]}"
        )

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a tough but fair PhD examiner. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        content = (response.choices[0].message.content or "").strip()

        import json
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        ai_data = json.loads(content)

        for q in ai_data.get("questions", []):
            result.examiner_questions.append(ExaminerQuestion(
                question=q.get("question", ""),
                category=q.get("category", "design"),
                expected_elements=[q.get("weakness_exploited", "")],
            ))

    except Exception as exc:
        logger.warning("AI methodology stress test failed: %s", exc)

    return result
