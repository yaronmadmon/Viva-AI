"""
Dissertation Planner -- creates a detailed, structured outline BEFORE any
writing begins.  This is the "blueprint" that ensures coherence, depth,
and proper academic argumentation across 50 000+ words.

The planner produces:
  1.  A subsection-level outline for every chapter
  2.  Argument threads that must weave through sections
  3.  Targeted search queries per subsection (for specific paper retrieval)
  4.  Section classification (all sections are ai_generated)
  5.  Target word counts per subsection

Pipeline position:  generate_plan() → per-subsection search → multi-pass write
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────

class SectionMode(str, Enum):
    """How much of a section the AI writes vs the student."""
    AI_GENERATED = "ai_generated"        # AI writes full prose
    STUDENT_TEMPLATE = "student_template" # AI writes structure, student fills data
    HYBRID = "hybrid"                     # AI writes frame, student customises


@dataclass
class SubsectionPlan:
    """Plan for one subsection (e.g. 'Literature Review > Theme 1')."""
    title: str
    target_words: int
    search_query: str                    # targeted paper query for THIS subsection
    instruction: str                     # writing instruction (prompt)
    mode: SectionMode = SectionMode.AI_GENERATED
    depends_on: List[str] = field(default_factory=list)   # subsection titles it references
    argument_threads: List[str] = field(default_factory=list)  # threads that must appear


@dataclass
class SectionPlan:
    """Plan for one major section (chapter)."""
    title: str
    artifact_type: str
    mode: SectionMode
    subsections: List[SubsectionPlan]
    target_words: int = 0  # computed from subsections

    def __post_init__(self):
        self.target_words = sum(s.target_words for s in self.subsections)


@dataclass
class ArgumentThread:
    """A through-line argument that must appear in multiple sections."""
    id: str
    description: str
    appears_in: List[str]   # section titles where it must be visible


@dataclass
class DissertationPlan:
    """Complete blueprint for a PhD dissertation."""
    topic: str
    description: str
    discipline: str
    sections: List[SectionPlan]
    argument_threads: List[ArgumentThread]
    total_target_words: int = 0

    def __post_init__(self):
        self.total_target_words = sum(s.target_words for s in self.sections)

    @property
    def all_search_queries(self) -> List[str]:
        """Unique search queries across all subsections."""
        seen = set()
        queries = []
        for sec in self.sections:
            for sub in sec.subsections:
                q = sub.search_query.strip()
                if q and q not in seen:
                    seen.add(q)
                    queries.append(q)
        return queries


# ── Plan builders per discipline ─────────────────────────────────────

def _stem_plan(topic: str, description: str) -> List[SectionPlan]:
    """STEM dissertation: ~55 000 words target."""
    t = topic  # shorthand for search queries

    return [
        # ── Introduction ──────────────────────────────────────────
        SectionPlan(
            title="Introduction",
            artifact_type="section",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Background and Context",
                    target_words=2000,
                    search_query=f"{t} background overview survey",
                    instruction=(
                        "Write the Background and Context for a STEM PhD introduction. "
                        "Situate the research area within its broader field. Every factual "
                        "claim MUST cite (Author, Year). Cover the evolution of the field, "
                        "current state, and why it matters. Write flowing academic paragraphs "
                        "with proper transitions. No bullet points."
                    ),
                ),
                SubsectionPlan(
                    title="Problem Statement",
                    target_words=1500,
                    search_query=f"{t} research gap challenges limitations",
                    instruction=(
                        "Write the Problem Statement. Define the specific gap or unresolved "
                        "question this dissertation addresses. State what is NOT known, not "
                        "just what is known. Ground the gap in specific cited evidence. "
                        "Use hedging: 'remains unclear', 'has not been adequately addressed'."
                    ),
                    argument_threads=["central_gap"],
                ),
                SubsectionPlan(
                    title="Intellectual Positioning",
                    target_words=1500,
                    search_query=f"{t} theoretical framework approach debate",
                    instruction=(
                        "Write the Intellectual Positioning subsection. Explicitly state: "
                        "(1) which school of thought or methodological tradition this work "
                        "aligns with, (2) at least ONE position this dissertation rejects or "
                        "modifies — name the scholars and explain why, (3) who would disagree "
                        "with this framing and on what grounds. This is NOT a literature "
                        "review — it is a statement of WHERE the author stands."
                    ),
                    argument_threads=["intellectual_stance"],
                ),
                SubsectionPlan(
                    title="Research Objectives and Hypotheses",
                    target_words=1200,
                    search_query=f"{t} research objectives hypotheses methodology",
                    instruction=(
                        "State specific, falsifiable research objectives and hypotheses. "
                        "Each hypothesis must be testable. Use the format: 'H1: [specific "
                        "prediction].' Link each objective to the gap identified above. "
                        "Scope precisely — state what this study will and will NOT examine."
                    ),
                    argument_threads=["central_gap", "research_questions"],
                ),
                SubsectionPlan(
                    title="Significance and Scope",
                    target_words=1000,
                    search_query=f"{t} significance impact applications scope",
                    instruction=(
                        "Describe the significance of this research but scope it precisely. "
                        "Use 'may contribute to' NOT 'will transform'. State explicit "
                        "boundary conditions: what populations, contexts, or domains this "
                        "does NOT cover. Distinguish theoretical from practical significance. "
                        "CLAIM DISCIPLINE: every sentence here is speculative — flag it as such."
                    ),
                ),
            ],
        ),

        # ── Literature Review ─────────────────────────────────────
        SectionPlan(
            title="Literature Review",
            artifact_type="section",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Theoretical Landscape",
                    target_words=2500,
                    search_query=f"{t} theoretical framework models taxonomy",
                    instruction=(
                        "Map the major theoretical camps and schools of thought relevant to "
                        "this topic. For each camp, name key proponents, their core "
                        "assumptions, and the evidence supporting their position. Organize "
                        "by THEME, not chronology. Write with academic depth — each camp "
                        "should be discussed in 2-3 substantial paragraphs."
                    ),
                    argument_threads=["intellectual_stance"],
                ),
                SubsectionPlan(
                    title="Empirical Evidence: Theme 1",
                    target_words=2500,
                    search_query=f"{t} empirical study experimental results performance",
                    instruction=(
                        "Review the first major theme of empirical evidence. For each study "
                        "cited: note the methods, sample size, key findings, AND limitations. "
                        "Do not just list studies — synthesize them, compare methodologies, "
                        "note where results converge and diverge. Include at least one NAMED "
                        "DISAGREEMENT: 'Author A found X, whereas Author B found Y. This "
                        "discrepancy appears to arise from differences in Z.'"
                    ),
                ),
                SubsectionPlan(
                    title="Empirical Evidence: Theme 2",
                    target_words=2500,
                    search_query=f"{t} comparative analysis evaluation benchmarks",
                    instruction=(
                        "Review the second major theme. Continue the same depth as Theme 1. "
                        "Focus on methodological variations across studies. Include at least "
                        "one NAMED DISAGREEMENT between specific authors. Show where the "
                        "evidence is strong and where it is inconclusive."
                    ),
                ),
                SubsectionPlan(
                    title="Empirical Evidence: Theme 3",
                    target_words=2000,
                    search_query=f"{t} clinical applications deployment challenges real-world",
                    instruction=(
                        "Review the third major theme. This theme should address practical "
                        "applications, deployment challenges, or real-world considerations. "
                        "Include NAMED DISAGREEMENT. Note the gap between lab performance "
                        "and real-world deployment."
                    ),
                ),
                SubsectionPlan(
                    title="Named Disagreements and Unresolved Debates",
                    target_words=2000,
                    search_query=f"{t} debate controversy disagreement limitations critique",
                    instruction=(
                        "This is a MANDATORY subsection. Consolidate and deepen the "
                        "disagreements identified above. Structure as: for each major "
                        "debate, present Author A's position, Author B's counterposition, "
                        "the evidence on each side, and why this debate matters for the "
                        "dissertation. Include at least 3 NAMED, SPECIFIC disagreements. "
                        "Do NOT use vague phrases like 'some scholars argue'. Always name "
                        "the scholars, their year, their specific claim."
                    ),
                    argument_threads=["literature_tensions"],
                ),
                SubsectionPlan(
                    title="Research Gap and Synthesis",
                    target_words=1500,
                    search_query=f"{t} research gap future work open questions",
                    instruction=(
                        "Synthesize the tensions and gaps identified above into a clear, "
                        "specific research gap. The gap must follow LOGICALLY from the "
                        "disagreements — not be a surprise. Frame it as: 'While Author A "
                        "has shown X and Author B has shown Y, NO study has yet examined Z "
                        "under conditions W.' This section MUST connect directly to the "
                        "Research Objectives stated in the Introduction."
                    ),
                    argument_threads=["central_gap", "literature_tensions"],
                    depends_on=["Research Objectives and Hypotheses"],
                ),
            ],
        ),

        # ── Methodology ───────────────────────────────────────────
        SectionPlan(
            title="Methodology",
            artifact_type="method",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Research Design and Justification",
                    target_words=2500,
                    search_query=f"{t} research methodology design comparative experimental",
                    instruction=(
                        "State the research design, then IMMEDIATELY justify it as a "
                        "defensive argument. Name at least 2-3 alternative designs that "
                        "were CONSIDERED AND REJECTED. For each: 'Alternative X was rejected "
                        "because Y.' This section must read as if anticipating examiner "
                        "attack on every choice."
                    ),
                    argument_threads=["methodology_defense"],
                ),
                SubsectionPlan(
                    title="Data Sources and Materials",
                    target_words=2000,
                    search_query=f"{t} dataset benchmark materials instruments",
                    instruction=(
                        "Describe all data sources, datasets, instruments, or materials with "
                        "precision. Select REAL, publicly available datasets appropriate to "
                        "the topic (e.g. TCGA, ISIC, CheXpert, ImageNet, MIMIC-III, UCI ML "
                        "Repository, or other well-known benchmarks). Include: provenance, "
                        "size, composition, known biases or limitations, and "
                        "validity/reliability evidence. Justify WHY these specific sources "
                        "and not alternatives. Provide concrete details: number of samples, "
                        "feature dimensions, class distributions, and access protocols."
                    ),
                ),
                SubsectionPlan(
                    title="Data Collection Procedures",
                    target_words=1500,
                    search_query=f"{t} data collection procedure protocol sampling",
                    instruction=(
                        "Describe the step-by-step data collection or experimental procedure "
                        "in sufficient detail for replication. Include sampling strategy, "
                        "inclusion/exclusion criteria, and timeline. Justify sample size "
                        "with power analysis or domain conventions. Write the COMPLETE "
                        "procedure as if this study was actually conducted: preprocessing "
                        "steps, train/validation/test splits, data augmentation techniques, "
                        "and quality control measures."
                    ),
                ),
                SubsectionPlan(
                    title="Analytical Methods",
                    target_words=2500,
                    search_query=f"{t} statistical analysis machine learning evaluation metrics",
                    instruction=(
                        "Describe every analytical method, statistical test, or computational "
                        "approach. For each: name the method, state WHY it was chosen over "
                        "alternatives, cite methodological references supporting its use, "
                        "and state its assumptions and limitations. Include evaluation "
                        "metrics and their justification."
                    ),
                    argument_threads=["methodology_defense"],
                ),
                SubsectionPlan(
                    title="Threats to Validity and Failure Conditions",
                    target_words=1500,
                    search_query=f"{t} validity threats limitations bias confounding",
                    instruction=(
                        "MANDATORY subsection. Structure as:\n"
                        "1. 'If this methodology fails, it fails because…' — name the "
                        "single weakest link.\n"
                        "2. Internal validity threats and mitigations.\n"
                        "3. External validity boundaries — to what populations/contexts "
                        "can findings be generalized?\n"
                        "4. Construct validity — do the measures actually capture the "
                        "intended constructs?\n"
                        "Be brutally honest. An examiner will respect acknowledged "
                        "limitations far more than hidden ones."
                    ),
                    argument_threads=["methodology_defense"],
                ),
                SubsectionPlan(
                    title="Ethical Considerations",
                    target_words=800,
                    search_query=f"{t} ethics IRB data protection consent",
                    instruction=(
                        "Write a COMPLETE ethical considerations section. Address: "
                        "IRB/ethics board approval framework (use a realistic institutional "
                        "review process, e.g. 'This study was reviewed under Protocol "
                        "#2024-XXX by the University Ethics Committee'), informed consent "
                        "procedures, data protection and privacy measures (GDPR/HIPAA "
                        "compliance where applicable), de-identification protocols, "
                        "potential harms and how they are mitigated, and data storage "
                        "and retention policies."
                    ),
                ),
            ],
        ),

        # ── Results ────────────────────────────────────────────────
        SectionPlan(
            title="Results",
            artifact_type="result",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Descriptive Overview",
                    target_words=1500,
                    search_query=f"{t} results descriptive statistics demographics",
                    instruction=(
                        "Write a COMPLETE descriptive overview with concrete, plausible "
                        "numbers. Generate realistic dataset statistics including: sample "
                        "size (N), demographic breakdowns, data quality metrics (missing "
                        "data rates, outlier counts), and response rates. Include markdown "
                        "tables with actual numbers, e.g.:\n\n"
                        "| Metric | Value |\n|--------|-------|\n"
                        "| Total samples | 12,458 |\n| Training set | 8,721 (70%) |\n\n"
                        "All numbers must be internally consistent and plausible for the "
                        "research topic. Report data quality checks, missing data handling "
                        "strategies, and normality assessments."
                    ),
                ),
                SubsectionPlan(
                    title="Findings by Research Question",
                    target_words=4000,
                    search_query=f"{t} results findings analysis outcomes",
                    instruction=(
                        "Write COMPLETE findings organized by each research question from "
                        "the Introduction. For each RQ/hypothesis, generate realistic "
                        "results including:\n"
                        "- The statistical test performed and its outcome\n"
                        "- Effect sizes (Cohen's d, eta-squared, or odds ratios)\n"
                        "- p-values and 95% confidence intervals\n"
                        "- Comparison tables with actual numbers, e.g.:\n\n"
                        "| Model | Accuracy | Precision | Recall | F1 | AUC |\n"
                        "|-------|----------|-----------|--------|-------|------|\n"
                        "| Baseline | 0.782 | 0.756 | 0.801 | 0.778 | 0.853 |\n"
                        "| Proposed | 0.891 | 0.874 | 0.903 | 0.888 | 0.941 |\n\n"
                        "State whether each hypothesis was supported or not supported. "
                        "All numbers must be internally consistent. Distinguish statistical "
                        "from practical significance."
                    ),
                    argument_threads=["research_questions"],
                ),
                SubsectionPlan(
                    title="Unexpected Findings",
                    target_words=1000,
                    search_query=f"{t} unexpected findings anomalies",
                    instruction=(
                        "Write about plausible unexpected or anomalous findings that "
                        "emerged from the analysis. Generate 2-3 realistic unexpected "
                        "patterns, such as: a subgroup that performed contrary to "
                        "expectations, a variable that showed an unexpected relationship, "
                        "or an outlier pattern that warrants further investigation. "
                        "Report these objectively with specific numbers, without "
                        "interpretation (save interpretation for the Discussion chapter)."
                    ),
                ),
            ],
        ),

        # ── Discussion ────────────────────────────────────────────
        SectionPlan(
            title="Discussion",
            artifact_type="discussion",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Interpretation of Key Findings",
                    target_words=3000,
                    search_query=f"{t} interpretation discussion implications findings",
                    instruction=(
                        "Interpret the research findings in context of the literature review. "
                        "For each key finding: (1) state what was found, (2) compare with "
                        "specific cited studies — where findings AGREE, cite the study; "
                        "where findings DISAGREE, name the study and explain the discrepancy. "
                        "(3) Discuss possible explanations for discrepancies.\n\n"
                        "CLAIM DISCIPLINE: Every interpretation must be hedged. Use 'these "
                        "results suggest' not 'these results prove'. Never claim causation "
                        "from correlational data."
                    ),
                    depends_on=["Findings by Research Question"],
                    argument_threads=["research_questions", "literature_tensions"],
                ),
                SubsectionPlan(
                    title="Comparison with Existing Literature",
                    target_words=3000,
                    search_query=f"{t} comparison prior work agreement disagreement",
                    instruction=(
                        "Systematically compare findings with the studies reviewed in the "
                        "Literature Review. Structure by theme. For EACH comparison: "
                        "name the specific authors, their findings, and how the current "
                        "results relate. Where there is disagreement, propose specific "
                        "methodological or contextual reasons. This section must reference "
                        "the Named Disagreements from the Lit Review and show whether this "
                        "dissertation's findings help resolve or complicate them."
                    ),
                    depends_on=["Named Disagreements and Unresolved Debates"],
                    argument_threads=["literature_tensions"],
                ),
                SubsectionPlan(
                    title="Theoretical and Practical Implications",
                    target_words=2500,
                    search_query=f"{t} theoretical implications practical applications recommendations",
                    instruction=(
                        "Discuss theoretical implications: how do findings modify, extend, "
                        "or challenge the theoretical positions from the Lit Review? Return "
                        "to the intellectual positioning from the Introduction.\n\n"
                        "Discuss practical implications: for whom, under what conditions. "
                        "Use 'may inform' NOT 'will transform'. Specify populations, "
                        "contexts, and necessary conditions.\n\n"
                        "CLAIM DISCIPLINE: This is where overreach is most common. EVERY "
                        "implication must include scope limitations."
                    ),
                    argument_threads=["intellectual_stance"],
                ),
                SubsectionPlan(
                    title="Limitations",
                    target_words=2000,
                    search_query=f"{t} limitations constraints caveats generalizability",
                    instruction=(
                        "MANDATORY, DETAILED limitations section. Do NOT bury in one "
                        "paragraph. For EACH limitation:\n"
                        "1. State the limitation clearly\n"
                        "2. Explain its specific impact on the findings\n"
                        "3. Suggest how future work could address it\n\n"
                        "Cover: sample limitations, methodological constraints, "
                        "measurement limitations, generalizability boundaries, temporal "
                        "constraints. An examiner respects honest limitation analysis."
                    ),
                    argument_threads=["methodology_defense"],
                ),
                SubsectionPlan(
                    title="Future Research Directions",
                    target_words=1500,
                    search_query=f"{t} future research directions open problems",
                    instruction=(
                        "Propose SPECIFIC, ACTIONABLE future research directions. Not "
                        "vague 'more research is needed' but concrete: 'A study using "
                        "[specific method] with [specific population] could test whether "
                        "[specific finding] holds under [specific condition].' Each "
                        "direction should address a specific limitation or open question "
                        "from this dissertation."
                    ),
                ),
            ],
        ),

        # ── Conclusion ────────────────────────────────────────────
        SectionPlan(
            title="Conclusion",
            artifact_type="section",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="Summary of Key Findings",
                    target_words=1500,
                    search_query=f"{t} conclusion summary key findings",
                    instruction=(
                        "Provide a precise, concise recapitulation of the key findings. "
                        "Do NOT introduce new information. Link each finding back to the "
                        "original research questions. Use past tense for what was found."
                    ),
                    depends_on=["Findings by Research Question"],
                    argument_threads=["research_questions"],
                ),
                SubsectionPlan(
                    title="Original Contribution",
                    target_words=1500,
                    search_query=f"{t} contribution novelty original advancement",
                    instruction=(
                        "MANDATORY FORMAT. State exactly 1-2 irreducible claims using "
                        "this frame: 'Before this dissertation, X was assumed/unknown. "
                        "This work demonstrates Y, which means Z.'\n\n"
                        "Each claim must be: (1) falsifiable, (2) narrow enough to be "
                        "defensible, (3) directly supported by the results. Reject any "
                        "contribution that is too broad or unfalsifiable."
                    ),
                    argument_threads=["central_gap"],
                ),
                SubsectionPlan(
                    title="Recommendations and Closing",
                    target_words=1000,
                    search_query=f"{t} recommendations policy practice",
                    instruction=(
                        "Provide actionable recommendations grounded in the evidence. "
                        "Scope each recommendation precisely. Close with broader "
                        "significance but NARROW scope in the final paragraph, do not "
                        "expand it. CLAIM DISCIPLINE: do NOT overstate. The final words "
                        "should be careful, not grandiose."
                    ),
                ),
            ],
        ),

        # ── References (auto-generated) ──────────────────────────
        SectionPlan(
            title="References",
            artifact_type="source",
            mode=SectionMode.AI_GENERATED,
            subsections=[
                SubsectionPlan(
                    title="References",
                    target_words=0,
                    search_query="",
                    instruction="SPECIAL:REFERENCES",
                ),
            ],
        ),
    ]


def _build_argument_threads(topic: str) -> List[ArgumentThread]:
    """Define the argument threads that must weave through the dissertation."""
    return [
        ArgumentThread(
            id="central_gap",
            description=f"The central research gap: what is not known about {topic}",
            appears_in=["Introduction", "Literature Review", "Conclusion"],
        ),
        ArgumentThread(
            id="intellectual_stance",
            description="The author's explicit theoretical/methodological position",
            appears_in=["Introduction", "Literature Review", "Discussion"],
        ),
        ArgumentThread(
            id="research_questions",
            description="The specific research questions and hypotheses",
            appears_in=["Introduction", "Results", "Discussion", "Conclusion"],
        ),
        ArgumentThread(
            id="literature_tensions",
            description="Named disagreements between specific authors in the field",
            appears_in=["Literature Review", "Discussion"],
        ),
        ArgumentThread(
            id="methodology_defense",
            description="Defensive justification of every methodological choice",
            appears_in=["Methodology", "Discussion"],
        ),
    ]


# ── AI-powered plan refinement ───────────────────────────────────────

async def _refine_plan_with_ai(
    plan: DissertationPlan,
) -> DissertationPlan:
    """Use GPT-4o-mini to refine the plan: identify specific themes for
    the literature review, tailor search queries, and adjust word targets.

    This is a PLANNING call, not a writing call — cheap and fast.
    """
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    if not key or key.startswith("sk-your-"):
        return plan  # no key, return generic plan

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)

    prompt = f"""You are a PhD dissertation planning expert. Given the topic and description below,
refine the literature review themes to be SPECIFIC to this research.

TOPIC: {plan.topic}
DESCRIPTION: {plan.description}
DISCIPLINE: {plan.discipline}

Current generic themes for Literature Review:
- Theme 1: "Empirical Evidence: Theme 1"
- Theme 2: "Empirical Evidence: Theme 2"  
- Theme 3: "Empirical Evidence: Theme 3"

Return EXACTLY 3 specific theme titles and their targeted search queries, formatted as:
THEME1_TITLE: [specific theme name]
THEME1_QUERY: [targeted academic search query]
THEME2_TITLE: [specific theme name]
THEME2_QUERY: [targeted academic search query]
THEME3_TITLE: [specific theme name]
THEME3_QUERY: [targeted academic search query]

Make themes specific to the topic. For example, if the topic is about deep learning
for cancer detection, themes might be:
- "CNN Architectures in Medical Imaging"
- "Vision Transformers for Radiological Analysis"
- "Interpretability and Clinical Trust in AI-Assisted Diagnosis"
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        text = (response.choices[0].message.content or "").strip()

        # Parse the response
        themes = {}
        for line in text.split("\n"):
            line = line.strip()
            for key_prefix in ["THEME1_TITLE:", "THEME1_QUERY:",
                               "THEME2_TITLE:", "THEME2_QUERY:",
                               "THEME3_TITLE:", "THEME3_QUERY:"]:
                if line.upper().startswith(key_prefix.upper()):
                    themes[key_prefix.rstrip(":")] = line[len(key_prefix):].strip()

        # Apply to plan
        lit_section = next((s for s in plan.sections if "Literature" in s.title), None)
        if lit_section:
            for i, key_num in enumerate(["1", "2", "3"]):
                title_key = f"THEME{key_num}_TITLE"
                query_key = f"THEME{key_num}_QUERY"
                # Find the generic theme subsection
                for sub in lit_section.subsections:
                    if f"Theme {key_num}" in sub.title and title_key in themes:
                        sub.title = f"Empirical Evidence: {themes[title_key]}"
                        sub.search_query = themes.get(query_key, sub.search_query)
                        break

        logger.info("Plan refined with AI-specific themes")
    except Exception as exc:
        logger.warning("Plan refinement failed (using generic): %s", exc)

    return plan


# ── Public API ────────────────────────────────────────────────────────

async def generate_plan(
    topic: str,
    description: str,
    discipline: str,
) -> DissertationPlan:
    """
    Generate a complete dissertation plan with subsection-level detail.

    Args:
        topic: Dissertation title
        description: Detailed description
        discipline: stem | humanities | social_sciences | legal | mixed

    Returns:
        DissertationPlan with all sections, subsections, search queries,
        argument threads, and word targets.
    """
    # Select discipline-specific plan builder
    builders = {
        "stem": _stem_plan,
        # humanities, social_sciences, legal use stem as base for now
        # (they will get their own in a future pass)
        "humanities": _stem_plan,
        "social_sciences": _stem_plan,
        "legal": _stem_plan,
        "mixed": _stem_plan,
    }

    builder = builders.get(discipline, _stem_plan)
    sections = builder(topic, description)
    threads = _build_argument_threads(topic)

    plan = DissertationPlan(
        topic=topic,
        description=description,
        discipline=discipline,
        sections=sections,
        argument_threads=threads,
    )

    # Refine with AI
    plan = await _refine_plan_with_ai(plan)

    logger.info(
        "Dissertation plan created: %d sections, %d subsections, %d target words",
        len(plan.sections),
        sum(len(s.subsections) for s in plan.sections),
        plan.total_target_words,
    )

    return plan
