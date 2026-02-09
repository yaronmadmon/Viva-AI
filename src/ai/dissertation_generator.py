"""
Dissertation Generator -- produces complete PhD-level content for each section
using real academic papers as grounding.

Pipeline:
  1. academic_search finds real papers
  2. Papers are grouped by relevance to each section
  3. OpenAI generates full, rigorous content grounded in those papers
  4. Each section is 1500-3000+ words of real academic writing
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.ai.academic_search import AcademicPaper, search_academic_papers
from src.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section definitions per discipline
# ---------------------------------------------------------------------------

SECTION_DEFS: Dict[str, List[Tuple[str, str, str]]] = {
    # (title, artifact_type, generation_instruction)
    #
    # ── Harvard-level prompt philosophy ─────────────────────────────────
    # Every section instruction enforces:
    #   1. CLAIM DISCIPLINE – scope every claim; prefer "suggests" over
    #      "demonstrates" unless statistical significance is stated; never
    #      claim generalizability beyond the stated sample/population.
    #   2. INTELLECTUAL POSITIONING – embed stance and disagreement inside
    #      Introduction and Literature Review (not a standalone chapter).
    #   3. METHODOLOGY AS ARGUMENT – every design choice anticipates
    #      examiner attack; rejected alternatives and failure conditions
    #      are mandatory.
    #   4. LITERATURE TENSION – named Author A vs Author B disagreements;
    #      unresolved debates, not just polite synthesis.
    #   5. CONTRIBUTION PRECISION – exactly 1-2 irreducible claims framed
    #      as "Before this dissertation … After, we know …".
    # ────────────────────────────────────────────────────────────────────

    "stem": [
        ("Introduction", "section",
         "Write a comprehensive PhD-level Introduction (2000+ words). "
         "Structure as follows:\n"
         "1. BACKGROUND & CONTEXT – Situate the research area with cited evidence. "
         "Every factual claim must cite (Author, Year).\n"
         "2. PROBLEM STATEMENT – Define the specific gap or unresolved question. "
         "State what is NOT known, not just what is known.\n"
         "3. INTELLECTUAL STANCE – Explicitly state which school of thought or "
         "methodological tradition this work aligns with. Name at least one "
         "position the dissertation rejects or modifies, and explain why. "
         "Identify who would disagree with this framing and on what grounds.\n"
         "4. RESEARCH OBJECTIVES & HYPOTHESES – State specific, falsifiable "
         "objectives. Each hypothesis must be testable.\n"
         "5. SIGNIFICANCE & SCOPE – Describe impact but scope it precisely. "
         "Use 'may contribute to' rather than 'will transform'. State explicit "
         "boundary conditions: what this study does NOT cover.\n"
         "CLAIM DISCIPLINE: Every sentence must be classified as descriptive "
         "(reporting facts), inferential (drawing conclusions), or speculative "
         "(projecting beyond evidence). Inferential sentences MUST include "
         "hedging language ('suggests', 'indicates', 'appears to'). "
         "Speculative sentences MUST be explicitly flagged with scope limitations."),

        ("Literature Review", "section",
         "Write a thorough PhD-level Literature Review (3000+ words). "
         "Organize thematically, NOT chronologically. Structure:\n"
         "1. THEORETICAL LANDSCAPE – Map the major schools of thought. For each "
         "camp, name key proponents and their core assumptions.\n"
         "2. EMPIRICAL EVIDENCE – For each theme, cite specific studies with "
         "methods, samples, and findings. Critically note sample sizes and "
         "generalizability limitations.\n"
         "3. NAMED DISAGREEMENTS (mandatory) – For EACH major theme, identify "
         "at least one unresolved debate. Use the format: 'Author A (Year) "
         "argues X, whereas Author B (Year) contends Y. This disagreement "
         "matters because Z.' Identify at least 3 named methodological or "
         "theoretical conflicts across the review.\n"
         "4. POINTS OF DISAGREEMENT subsection – Explicitly address: which "
         "assumptions in the literature this dissertation challenges, which "
         "methodological approaches are problematic and why, and where the "
         "author's position diverges from the dominant view.\n"
         "5. RESEARCH GAP – Synthesize tensions into a clear, specific gap. "
         "The gap must follow logically from the disagreements above.\n"
         "CLAIM DISCIPLINE: Never write 'the literature shows' or 'research "
         "proves'. Use 'evidence suggests', 'findings indicate'. Penalize "
         "vague attribution ('some scholars argue…') – always name the scholars."),

        ("Methodology", "method",
         "Write a detailed PhD-level Methodology section (2000+ words). "
         "This section must read as a DEFENSIVE ARGUMENT, not a procedure "
         "description. Every choice must anticipate examiner attack. Structure:\n"
         "1. RESEARCH DESIGN & JUSTIFICATION – State the design clearly, then "
         "IMMEDIATELY justify it. Name at least 2-3 alternative designs that "
         "were considered and explicitly rejected. For each rejection, state: "
         "'Alternative X was rejected because Y.'\n"
         "2. MATERIALS & INSTRUMENTS – Describe with precision. Include "
         "validity/reliability evidence for each instrument.\n"
         "3. DATA COLLECTION – Procedures, sample/population, variables. "
         "State why THIS sample and not a broader/narrower one.\n"
         "4. ANALYTICAL METHODS – Specific statistical tests or qualitative "
         "approaches. Justify each choice against alternatives.\n"
         "5. FAILURE CONDITIONS (mandatory) – A subsection titled 'Threats to "
         "Validity and Failure Conditions'. State: 'If this methodology fails, "
         "it fails because…' Cover internal validity threats, external validity "
         "boundaries, and construct validity concerns.\n"
         "6. BOUNDARY CONDITIONS (mandatory) – The exact scope within which "
         "findings are valid. What populations, contexts, or timeframes are "
         "explicitly excluded.\n"
         "7. ETHICAL CONSIDERATIONS – IRB/ethics approval, informed consent, "
         "data protection.\n"
         "CLAIM DISCIPLINE: Never claim the methodology 'ensures' or "
         "'guarantees'. Use 'is designed to minimize', 'aims to control for'."),

        ("Results", "result",
         "Write a comprehensive PhD-level Results section (2000+ words). "
         "Present findings organized by research question. Structure:\n"
         "1. DESCRIPTIVE OVERVIEW – Sample characteristics, response rates, "
         "data quality checks.\n"
         "2. FINDINGS BY RESEARCH QUESTION – For each question/hypothesis: "
         "state the test, report the result with effect sizes and confidence "
         "intervals, note whether the hypothesis was supported.\n"
         "3. UNEXPECTED FINDINGS – Report anomalies honestly.\n"
         "4. TABLES & FIGURES – Describe what each would contain (table "
         "summaries, figure descriptions).\n"
         "CLAIM DISCIPLINE: Report results OBJECTIVELY. Use 'the data indicate' "
         "not 'the data prove'. Never interpret in this section – that belongs "
         "in Discussion. Always report effect sizes alongside p-values. "
         "Distinguish between statistical significance and practical significance."),

        ("Discussion", "discussion",
         "Write a rigorous PhD-level Discussion section (2500+ words). Structure:\n"
         "1. INTERPRETATION OF FINDINGS – For each key result, interpret in "
         "context of the literature review. Where findings AGREE with prior "
         "work, cite the specific studies. Where findings DISAGREE, name "
         "the specific studies and explain why the discrepancy exists.\n"
         "2. THEORETICAL IMPLICATIONS – How do findings modify, extend, or "
         "challenge the theoretical positions identified in the Literature Review? "
         "Return to the intellectual positioning from the Introduction.\n"
         "3. PRACTICAL IMPLICATIONS – Scope these carefully. Use 'may inform' "
         "not 'will transform'. Specify for whom and under what conditions.\n"
         "4. LIMITATIONS (mandatory, detailed) – For each limitation: state it, "
         "explain its impact on findings, and suggest how future work could "
         "address it. Do NOT bury limitations in a single paragraph.\n"
         "5. FUTURE RESEARCH – Specific, actionable directions, not vague "
         "calls for 'more research'.\n"
         "CLAIM DISCIPLINE: This is the section where overreach is most common. "
         "Every inferential statement must include scope limitations. Never "
         "claim findings are 'generalizable' without explicitly stating to what "
         "population and under what conditions."),

        ("Conclusion", "section",
         "Write a strong PhD-level Conclusion (1000+ words). Structure:\n"
         "1. SUMMARY OF KEY FINDINGS – Brief, precise recapitulation.\n"
         "2. ORIGINAL CONTRIBUTION (mandatory format) – State exactly 1-2 "
         "irreducible claims using this frame: 'Before this dissertation, X "
         "was assumed/unknown. This work shows Y, which means Z.' Reject any "
         "contribution that cannot be falsified or that is too broad.\n"
         "3. RECOMMENDATIONS – For practitioners, policymakers, or the field. "
         "Scope each recommendation to its evidence base.\n"
         "4. CLOSING – Broader significance, stated carefully.\n"
         "CLAIM DISCIPLINE: The conclusion must be almost painfully careful. "
         "Do NOT introduce new claims. Do NOT overstate impact. The final "
         "paragraphs should narrow scope, not expand it."),

        ("References", "source",
         "SPECIAL:REFERENCES"),
    ],

    "humanities": [
        ("Introduction", "section",
         "Write a compelling PhD-level Introduction for a humanities dissertation "
         "(2000+ words). Structure:\n"
         "1. OPENING & INTELLECTUAL CONTEXT – Engage the reader, then situate "
         "the work within the scholarly conversation. Name the key debates.\n"
         "2. CENTRAL THESIS – State the thesis clearly and precisely. The thesis "
         "must be arguable (someone could reasonably disagree).\n"
         "3. INTELLECTUAL STANCE (mandatory) – Explicitly state which "
         "interpretive tradition, theoretical school, or critical approach "
         "this work adopts. Name at least one position the dissertation rejects "
         "or modifies, and explain why. Identify who would disagree with this "
         "framing and on what grounds.\n"
         "4. RESEARCH QUESTIONS – Specific questions that structure the inquiry.\n"
         "5. METHODOLOGICAL APPROACH – Close reading, discourse analysis, "
         "archival research, etc. Justify the choice.\n"
         "6. STRUCTURE OF THE ARGUMENT – Outline how the argument builds.\n"
         "CLAIM DISCIPLINE: Distinguish between descriptive claims (reporting "
         "what scholars have said), interpretive claims (your reading of "
         "texts/evidence), and speculative claims (broader implications). "
         "Every interpretive claim must be grounded in textual evidence."),

        ("Theoretical Framework", "section",
         "Write a rigorous PhD-level Theoretical Framework (2500+ words). Structure:\n"
         "1. TRADITIONS & THINKERS – Identify the philosophical/critical "
         "traditions informing the analysis. For each tradition, name key "
         "thinkers, core concepts, and how they apply.\n"
         "2. TENSIONS BETWEEN FRAMEWORKS – Where do these traditions disagree? "
         "If combining multiple frameworks, justify why they are compatible "
         "and where friction exists.\n"
         "3. APPLICATION TO RESEARCH MATERIAL – How specifically does this "
         "framework illuminate the research questions?\n"
         "4. LIMITATIONS OF THE FRAMEWORK – What does this lens NOT capture? "
         "What alternative frameworks would see differently?\n"
         "CLAIM DISCIPLINE: Distinguish between 'X argues' (reporting) and "
         "'I contend' (your interpretive claim). Never attribute to a thinker "
         "a position they did not hold."),

        ("Literature Review", "section",
         "Write a thorough PhD-level Literature Review (3000+ words). "
         "Organize by SCHOLARLY CONVERSATIONS, not chronologically. Structure:\n"
         "1. SCHOLARLY CAMPS – Map the major positions in the field. For each "
         "camp, name key scholars and their core arguments.\n"
         "2. NAMED DISAGREEMENTS (mandatory) – For each major conversation, "
         "identify at least one unresolved debate: 'Scholar A (Year) reads X "
         "as Y, whereas Scholar B (Year) contends Z. This matters because…' "
         "Identify at least 3 substantive scholarly conflicts.\n"
         "3. POINTS OF DISAGREEMENT subsection – State explicitly: which "
         "readings or interpretations this dissertation challenges, whose "
         "assumptions are being questioned, and where the author's position "
         "diverges from established scholarship.\n"
         "4. GAP IN THE CONVERSATION – What has not been said, read, or "
         "analyzed? The gap must follow from the tensions above.\n"
         "CLAIM DISCIPLINE: Never write 'scholars agree' without naming them. "
         "Never use 'some argue' – always specify who argues what."),

        ("Analysis", "section",
         "Write an in-depth PhD-level Analysis section (3000+ words). Structure:\n"
         "1. CLOSE READING / CRITICAL ANALYSIS – Engage with primary sources, "
         "texts, or cases with precision. Every interpretive claim must point "
         "to specific textual evidence (quote, passage, scene, document).\n"
         "2. PATTERNS & TENSIONS – Draw connections across analyses. Identify "
         "where your readings create productive tension.\n"
         "3. COUNTERARGUMENTS – For each major interpretive claim, acknowledge "
         "how an alternative reading would interpret the same evidence.\n"
         "CLAIM DISCIPLINE: Mark the difference between 'the text shows' "
         "(descriptive) and 'I read this as' (interpretive). Never claim a "
         "text 'proves' an argument – texts support, suggest, or complicate."),

        ("Discussion", "discussion",
         "Write a PhD-level Discussion (2000+ words). Structure:\n"
         "1. ARGUMENT SYNTHESIS – Develop the central argument by connecting "
         "analyses. Show how findings across sections build cumulatively.\n"
         "2. ENGAGEMENT WITH COUNTERARGUMENTS – Name specific scholars who "
         "would challenge your reading. Address their objections directly.\n"
         "3. BROADER SIGNIFICANCE – Connect to contemporary debates, but "
         "scope carefully. Use 'this analysis suggests' not 'this proves'.\n"
         "4. LIMITATIONS – What texts, archives, or perspectives were "
         "excluded? What would a different theoretical lens reveal?\n"
         "CLAIM DISCIPLINE: Distinguish clearly between what your evidence "
         "supports and what you speculate it might imply."),

        ("Conclusion", "section",
         "Write a PhD-level Conclusion (1000+ words). Structure:\n"
         "1. THESIS RESTATEMENT – Brief, precise.\n"
         "2. ORIGINAL CONTRIBUTION (mandatory format) – State exactly 1-2 "
         "irreducible claims: 'Before this dissertation, X was assumed/unread/"
         "unexamined. This work shows Y, which means Z.' The contribution "
         "must be falsifiable or at least substantively arguable.\n"
         "3. LIMITATIONS – Acknowledge honestly.\n"
         "4. BROADER SIGNIFICANCE – Carefully scoped.\n"
         "CLAIM DISCIPLINE: Do NOT overstate. Do NOT introduce new arguments. "
         "Narrow scope in the final paragraphs."),

        ("Bibliography", "source",
         "SPECIAL:REFERENCES"),
    ],

    "social_sciences": [
        ("Introduction", "section",
         "Write a comprehensive PhD-level Introduction for a social sciences "
         "dissertation (2000+ words). Structure:\n"
         "1. BACKGROUND & CONTEXT – Situate the research problem with cited "
         "evidence. Every factual claim must cite (Author, Year).\n"
         "2. PROBLEM STATEMENT – Define the specific gap. State what is NOT "
         "known, not just what is known.\n"
         "3. INTELLECTUAL STANCE (mandatory) – State which theoretical "
         "tradition or paradigm this work adopts (e.g., constructivist, "
         "positivist, critical realist). Name at least one position the "
         "dissertation rejects or modifies, and explain why. Identify who "
         "would disagree with this framing.\n"
         "4. RESEARCH QUESTIONS & HYPOTHESES – Specific, testable.\n"
         "5. SIGNIFICANCE – Why this matters, scoped to specific populations "
         "or contexts. Use 'may contribute to' rather than 'will transform'.\n"
         "6. DEFINITION OF KEY TERMS – Operational definitions.\n"
         "7. SCOPE & DELIMITATIONS – Explicit boundaries.\n"
         "CLAIM DISCIPLINE: Inferential statements require hedging. "
         "Speculative statements require explicit scope limitations."),

        ("Literature Review", "section",
         "Write a thorough PhD-level Literature Review (3000+ words). "
         "Organize thematically. Structure:\n"
         "1. THEORETICAL FOUNDATION – Map competing theoretical positions. "
         "Name proponents and their core assumptions.\n"
         "2. EMPIRICAL REVIEW – For each theme, cite studies with methods, "
         "samples, and findings. Note sample size limitations and contextual "
         "constraints.\n"
         "3. NAMED DISAGREEMENTS (mandatory) – For each theme, identify at "
         "least one unresolved debate: 'Author A (Year) found X using method "
         "M1, whereas Author B (Year) found Y using M2. This discrepancy "
         "suggests…' Include at least 3 named conflicts.\n"
         "4. POINTS OF DISAGREEMENT subsection – State which assumptions "
         "in the literature this dissertation challenges and why. "
         "Identify methodological weaknesses in prior work.\n"
         "5. RESEARCH GAP – Emerges logically from the tensions above.\n"
         "CLAIM DISCIPLINE: Never use 'research proves' or 'the literature "
         "shows'. Use 'evidence suggests', 'findings indicate'. Always name "
         "specific scholars, never 'some researchers'."),

        ("Methodology", "method",
         "Write a detailed PhD-level Methodology section (2500+ words). "
         "This section must read as a DEFENSIVE ARGUMENT. Structure:\n"
         "1. RESEARCH DESIGN & JUSTIFICATION – State design (quantitative/ "
         "qualitative/mixed), then justify. Name at least 2 alternative "
         "designs considered and rejected. For each: 'Alternative X was "
         "rejected because Y.'\n"
         "2. POPULATION & SAMPLING – Who, why this group, and why not a "
         "different population. Justify sample size.\n"
         "3. DATA COLLECTION INSTRUMENTS – Describe with validity/reliability "
         "evidence. Justify each instrument against alternatives.\n"
         "4. PROCEDURES – Step by step, replicable.\n"
         "5. DATA ANALYSIS PLAN – Specific statistical tests or coding "
         "approaches. Justify each against alternatives.\n"
         "6. FAILURE CONDITIONS (mandatory) – 'If this methodology fails, it "
         "fails because…' Cover threats to internal, external, and construct "
         "validity.\n"
         "7. BOUNDARY CONDITIONS (mandatory) – Exact populations, contexts, "
         "and timeframes within which findings are valid.\n"
         "8. ETHICAL CONSIDERATIONS – IRB/ethics, consent, data protection.\n"
         "CLAIM DISCIPLINE: Never say methodology 'ensures' or 'guarantees'. "
         "Use 'is designed to minimize', 'aims to control for'."),

        ("Results", "result",
         "Write a comprehensive PhD-level Results section (2000+ words). Structure:\n"
         "1. DESCRIPTIVE OVERVIEW – Demographics, response rates, data quality.\n"
         "2. FINDINGS BY RESEARCH QUESTION – Report with effect sizes, "
         "confidence intervals. State whether hypotheses were supported.\n"
         "3. QUALITATIVE THEMES – With specific evidence/quotes.\n"
         "4. UNEXPECTED FINDINGS – Report honestly.\n"
         "CLAIM DISCIPLINE: Report OBJECTIVELY. Use 'the data indicate' not "
         "'the data prove'. Distinguish statistical from practical significance. "
         "Do NOT interpret – save for Discussion."),

        ("Discussion", "discussion",
         "Write a rigorous PhD-level Discussion (2500+ words). Structure:\n"
         "1. INTERPRETATION – For each finding, connect to specific cited "
         "studies. Where findings agree, cite the studies. Where they disagree, "
         "name the studies and explain the discrepancy.\n"
         "2. THEORETICAL IMPLICATIONS – How findings extend, modify, or "
         "challenge the theoretical positions from the Literature Review.\n"
         "3. PRACTICAL IMPLICATIONS – Scoped carefully. For whom, under what "
         "conditions. Use 'may inform' not 'will transform'.\n"
         "4. LIMITATIONS (mandatory, detailed) – For each limitation: state "
         "it, explain its impact, and suggest how future work addresses it.\n"
         "5. FUTURE RESEARCH – Specific and actionable.\n"
         "CLAIM DISCIPLINE: Never claim 'generalizability' without specifying "
         "to what population and under what conditions. Every inferential "
         "statement must include scope limitations."),

        ("Conclusion", "section",
         "Write a PhD-level Conclusion (1000+ words). Structure:\n"
         "1. SUMMARY – Brief recapitulation of key findings.\n"
         "2. ORIGINAL CONTRIBUTION (mandatory format) – State exactly 1-2 "
         "irreducible claims: 'Before this dissertation, X was assumed. This "
         "work shows Y, which means Z.' Reject any contribution that is too "
         "broad or unfalsifiable.\n"
         "3. FINAL REFLECTIONS – Broader significance, carefully scoped.\n"
         "CLAIM DISCIPLINE: Do NOT introduce new claims. Do NOT overstate "
         "impact. Narrow scope in final paragraphs."),

        ("References", "source",
         "SPECIAL:REFERENCES"),
    ],

    "legal": [
        ("Introduction", "section",
         "Write a PhD-level Introduction for a legal dissertation (2000+ words). "
         "Structure:\n"
         "1. LEGAL ISSUE & CONTEXT – Introduce the legal problem with "
         "specific reference to statutes, cases, or regulatory frameworks.\n"
         "2. RESEARCH QUESTION – Precise and answerable.\n"
         "3. INTELLECTUAL STANCE (mandatory) – State which doctrinal tradition "
         "or jurisprudential school this work adopts (e.g., legal positivism, "
         "critical legal studies, law and economics). Name at least one position "
         "or established interpretation this dissertation challenges.\n"
         "4. SIGNIFICANCE – Why this question matters now. Scope to specific "
         "jurisdictions and contexts.\n"
         "5. METHODOLOGY – Doctrinal, comparative, empirical, or mixed. "
         "Justify the choice against alternatives.\n"
         "6. STRUCTURE – Outline the argument's progression.\n"
         "CLAIM DISCIPLINE: Distinguish between established legal doctrine "
         "(descriptive), interpretive arguments (inferential), and policy "
         "recommendations (speculative). Each category requires different "
         "levels of authority support."),

        ("Legal Framework", "section",
         "Write a detailed PhD-level Legal Framework (2500+ words). Structure:\n"
         "1. CONSTITUTIONAL / STATUTORY PROVISIONS – Relevant legislation "
         "with specific section references.\n"
         "2. CASE LAW – Holdings, reasoning, and significance. Include "
         "dissenting opinions where they illuminate the argument.\n"
         "3. REGULATORY FRAMEWORK – Relevant regulations, guidelines.\n"
         "4. INTERNATIONAL / COMPARATIVE – Relevant principles from other "
         "jurisdictions.\n"
         "5. DOCTRINAL TENSIONS (mandatory) – Where does the legal framework "
         "contain internal contradictions, evolving interpretations, or "
         "unresolved questions? Name specific cases or commentators on "
         "each side of unresolved doctrinal debates.\n"
         "CLAIM DISCIPLINE: Distinguish between binding authority (must follow), "
         "persuasive authority (may consider), and academic commentary "
         "(scholarly opinion). Never treat commentary as binding."),

        ("Literature Review", "section",
         "Write a thorough PhD-level Literature Review (2500+ words). Structure:\n"
         "1. DOCTRINAL COMMENTARY – Major scholarly positions on the legal "
         "issue. Name specific commentators.\n"
         "2. CRITICAL PERSPECTIVES – Alternative approaches (e.g., feminist "
         "legal theory, law and economics, socio-legal). Name scholars.\n"
         "3. NAMED DISAGREEMENTS (mandatory) – For each major issue, identify "
         "at least one scholarly debate: 'Commentator A (Year) argues X, "
         "whereas Commentator B (Year) contends Y.' Include at least 3 "
         "named conflicts.\n"
         "4. POINTS OF DISAGREEMENT subsection – Where does this dissertation "
         "challenge established commentary or conventional interpretation?\n"
         "5. GAP – What has not been analyzed, compared, or critiqued?\n"
         "CLAIM DISCIPLINE: Distinguish between reporting what scholars argue "
         "and the author's own position. Always name specific commentators."),

        ("Analysis", "section",
         "Write an in-depth PhD-level Legal Analysis (3000+ words). "
         "Apply the legal framework to the research question. Structure:\n"
         "1. APPLICATION OF LAW TO FACTS – Systematic, precise.\n"
         "2. CASE ANALYSIS – Detailed analysis of relevant cases. For each: "
         "facts, holding, reasoning, and significance for the argument.\n"
         "3. SCHOLARLY ARGUMENTS – Engage with the positions from the Lit "
         "Review. Where you agree, say why. Where you disagree, counter "
         "with specific authority.\n"
         "4. COUNTERARGUMENTS – Anticipate opposing interpretations and "
         "address them directly.\n"
         "CLAIM DISCIPLINE: Every legal argument must be supported by "
         "authority. Policy arguments must be clearly flagged as such."),

        ("Comparative Perspective", "section",
         "Write a PhD-level Comparative Perspective (2000+ words). Structure:\n"
         "1. JURISDICTIONAL COMPARISON – Compare approaches across at least "
         "2 jurisdictions. For each: legal framework, key cases, outcomes.\n"
         "2. STRENGTHS & WEAKNESSES – Of each jurisdiction's approach.\n"
         "3. LESSONS – What can be transplanted vs. what is jurisdiction-"
         "specific? Be precise about contextual differences.\n"
         "CLAIM DISCIPLINE: Never assume transplantability. Always caveat "
         "comparative conclusions with contextual differences."),

        ("Conclusion & Recommendations", "section",
         "Write a PhD-level Conclusion with Recommendations (1500+ words). "
         "Structure:\n"
         "1. SUMMARY OF FINDINGS – Brief recapitulation.\n"
         "2. ORIGINAL CONTRIBUTION (mandatory format) – State exactly 1-2 "
         "irreducible claims: 'Before this dissertation, the prevailing "
         "interpretation of X was Y. This analysis shows Z, which means…'\n"
         "3. RECOMMENDATIONS – Legislative, judicial, or policy proposals. "
         "Each must be grounded in the analysis, not general aspiration.\n"
         "4. LIMITATIONS – Jurisdictional, temporal, methodological.\n"
         "CLAIM DISCIPLINE: Recommendations must be scoped. Do NOT recommend "
         "sweeping reform without evidentiary basis in the analysis."),

        ("Table of Authorities", "source",
         "SPECIAL:REFERENCES"),
    ],
}

# Fallback
SECTION_DEFS["mixed"] = SECTION_DEFS["social_sciences"]


# ---------------------------------------------------------------------------
# OpenAI section writer
# ---------------------------------------------------------------------------

async def _generate_section_with_openai(
    topic: str,
    description: str,
    section_title: str,
    instruction: str,
    papers: List[AcademicPaper],
    discipline: str,
    all_section_titles: List[str],
) -> str:
    """Call OpenAI to generate one dissertation section grounded in real papers."""
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder:
        # No real key -- generate a structured stub with paper references
        return _generate_stub_section(topic, description, section_title, instruction, papers, discipline)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)

    # Build the papers context
    papers_context = _build_papers_context(papers)

    system_prompt = (
        "You are a world-class academic researcher writing a PhD dissertation "
        "that would pass examination at a top-tier university (Harvard, Oxford, "
        "Cambridge). You write rigorous, publication-quality academic prose.\n\n"

        "CITATION RULES:\n"
        "- You MUST cite the provided real papers using (Author, Year) format.\n"
        "- Every major claim must be grounded in the provided literature.\n"
        "- Never use vague attribution ('some scholars argue…'). Always name "
        "the scholar(s).\n\n"

        "CLAIM DISCIPLINE (critical – examiners are extremely sensitive to this):\n"
        "- Classify every claim as DESCRIPTIVE (reporting facts), INFERENTIAL "
        "(drawing conclusions), or SPECULATIVE (projecting beyond evidence).\n"
        "- Descriptive claims require citations.\n"
        "- Inferential claims MUST use hedging: 'suggests', 'indicates', "
        "'appears to', 'may'. NEVER use 'proves', 'demonstrates conclusively', "
        "'establishes beyond doubt'.\n"
        "- Speculative claims MUST include explicit scope limitations and "
        "future-research framing.\n"
        "- Never claim generalizability beyond the stated sample/population.\n"
        "- Prefer 'this study contributes to understanding of X' over "
        "'this study solves X'.\n"
        "- Distinguish statistical significance from practical significance.\n\n"

        "INTELLECTUAL POSITIONING:\n"
        "- When the instruction asks for intellectual stance, you MUST take "
        "a clear position within scholarly debates, not just report them.\n"
        "- Name specific scholars on each side of debates.\n"
        "- State which positions you align with, which you reject, and why.\n\n"

        "LITERATURE TENSION:\n"
        "- Literature reviews must contain NAMED DISAGREEMENTS between "
        "specific authors (Author A vs Author B).\n"
        "- Identify unresolved debates, not just synthesize consensus.\n"
        "- Show where methodological assumptions are contested.\n\n"

        "METHODOLOGY AS ARGUMENT:\n"
        "- Every methodological choice must be justified against alternatives.\n"
        "- Name rejected alternatives and explain why.\n"
        "- Include failure conditions and boundary conditions.\n\n"

        "STYLE:\n"
        "- Write flowing academic paragraphs, not bullet points.\n"
        "- Use proper academic transitions between sections.\n"
        "- Do NOT use excessive markdown headers.\n"
        "- The writing should be indistinguishable from a real PhD dissertation."
    )

    user_prompt = f"""Write the "{section_title}" section of a PhD dissertation.

DISSERTATION TOPIC: {topic}
DESCRIPTION: {description}
DISCIPLINE: {discipline}
ALL SECTIONS IN THIS DISSERTATION: {', '.join(all_section_titles)}

INSTRUCTION: {instruction}

REAL ACADEMIC PAPERS TO CITE (you MUST reference these):
{papers_context}

Write the full section now. Start with a section heading "## {section_title}" and write comprehensive, 
PhD-quality academic content. Cite the real papers above by author name and year. 
Aim for at least the word count specified in the instruction.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.7,
        )
        content = (response.choices[0].message.content or "").strip()
        if content:
            return content
    except Exception as exc:
        logger.error("OpenAI generation failed for '%s': %s", section_title, exc)

    # Fallback to stub
    return _generate_stub_section(topic, description, section_title, instruction, papers, discipline)


def _build_papers_context(papers: List[AcademicPaper], max_papers: int = 25) -> str:
    """Build a text block of paper summaries for the prompt."""
    lines = []
    for i, p in enumerate(papers[:max_papers], 1):
        cite = p.short_cite
        abstract_snippet = ""
        if p.abstract:
            words = p.abstract.split()[:80]
            abstract_snippet = " ".join(words)
            if len(p.abstract.split()) > 80:
                abstract_snippet += "..."
        journal_str = f" Published in: {p.journal}." if p.journal else ""
        cited = f" Cited {p.citation_count} times." if p.citation_count else ""
        lines.append(
            f"[{i}] {cite}: \"{p.title}\"{journal_str}{cited}\n"
            f"    Abstract: {abstract_snippet or '(not available)'}"
        )
    return "\n\n".join(lines)


def _generate_references_section(papers: List[AcademicPaper]) -> str:
    """Generate a proper references / bibliography section from real papers."""
    lines = ["## References\n"]
    for p in papers:
        lines.append(p.apa_reference)
        lines.append("")
    return "\n".join(lines)


def _generate_stub_section(
    topic: str,
    description: str,
    section_title: str,
    instruction: str,
    papers: List[AcademicPaper],
    discipline: str,
) -> str:
    """Generate a rich stub section when OpenAI key is not available.
    Uses real paper data to create structured content."""

    lines = [f"## {section_title}\n"]

    if not papers:
        lines.append(
            f"This section covers the {section_title.lower()} of the dissertation on "
            f"\"{topic}\". Content generation requires an OpenAI API key to produce "
            f"full PhD-level writing. Configure OPENAI_API_KEY in your .env file.\n"
        )
        return "\n".join(lines)

    # Write content referencing real papers
    lines.append(
        f"The following {section_title.lower()} examines the research landscape "
        f"surrounding {topic.lower()}. This analysis draws upon {len(papers)} "
        f"peer-reviewed publications sourced from Semantic Scholar, OpenAlex, and CrossRef.\n"
    )

    # Group papers and create paragraphs
    top_cited = sorted(papers, key=lambda p: p.citation_count, reverse=True)[:10]
    recent = sorted([p for p in papers if p.year and p.year >= 2020], key=lambda p: p.year or 0, reverse=True)[:10]

    if top_cited:
        lines.append("### Key Foundational Works\n")
        lines.append(
            "The study of this topic is grounded in several highly influential works. "
        )
        for p in top_cited[:5]:
            abstract_bit = ""
            if p.abstract:
                words = p.abstract.split()[:40]
                abstract_bit = " " + " ".join(words) + ("..." if len(p.abstract.split()) > 40 else "")
            lines.append(
                f"{p.short_cite} investigated \"{p.title}\" "
                f"(cited {p.citation_count} times).{abstract_bit}\n"
            )

    if recent:
        lines.append("\n### Recent Developments\n")
        lines.append("Recent scholarship has expanded the field significantly:\n")
        for p in recent[:5]:
            journal_str = f" in *{p.journal}*" if p.journal else ""
            lines.append(f"- {p.short_cite}, \"{p.title}\"{journal_str}")
        lines.append("")

    lines.append(
        f"\n*Note: This is a structured outline based on {len(papers)} real academic papers. "
        f"To generate full PhD-level prose, configure your OpenAI API key in .env.*\n"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main generation pipeline
# ---------------------------------------------------------------------------

@dataclass
class GeneratedSection:
    """One generated dissertation section."""
    title: str
    artifact_type: str
    content: str
    word_count: int
    papers_used: int


@dataclass
class GeneratedDissertation:
    """Complete generated dissertation."""
    topic: str
    discipline: str
    sections: List[GeneratedSection]
    total_papers: int
    total_words: int
    papers: List[AcademicPaper]


async def generate_dissertation(
    topic: str,
    description: str,
    discipline: str,
) -> GeneratedDissertation:
    """
    Generate a complete PhD dissertation grounded in real academic papers.

    1. Searches academic APIs for relevant papers
    2. Generates each section using OpenAI (or stubs) with real citations
    3. Returns the full dissertation

    Args:
        topic: Dissertation title / topic
        description: Detailed description of the research
        discipline: One of stem, humanities, social_sciences, legal, mixed

    Returns:
        GeneratedDissertation with all sections
    """
    logger.info("Starting dissertation generation for: %s [%s]", topic, discipline)

    # Step 1: Find real papers
    search_query = f"{topic} {description or ''}"[:200]
    papers = await search_academic_papers(search_query, max_results=40)
    logger.info("Found %d academic papers", len(papers))

    # Step 2: Get section definitions
    sections_def = SECTION_DEFS.get(discipline, SECTION_DEFS["mixed"])
    all_titles = [s[0] for s in sections_def]

    # Step 3: Generate each section
    # Run sections sequentially to respect rate limits
    generated_sections: List[GeneratedSection] = []
    total_words = 0

    for title, artifact_type, instruction in sections_def:
        if instruction == "SPECIAL:REFERENCES":
            # Generate references from the actual papers
            content = _generate_references_section(papers)
        else:
            content = await _generate_section_with_openai(
                topic=topic,
                description=description or topic,
                section_title=title,
                instruction=instruction,
                papers=papers,
                discipline=discipline,
                all_section_titles=all_titles,
            )

        wc = len(content.split())
        total_words += wc
        generated_sections.append(GeneratedSection(
            title=title,
            artifact_type=artifact_type,
            content=content,
            word_count=wc,
            papers_used=len(papers),
        ))
        logger.info("  Generated '%s': %d words", title, wc)

    result = GeneratedDissertation(
        topic=topic,
        discipline=discipline,
        sections=generated_sections,
        total_papers=len(papers),
        total_words=total_words,
        papers=papers,
    )
    logger.info(
        "Dissertation generation complete: %d sections, %d words, %d papers",
        len(generated_sections), total_words, len(papers),
    )
    return result
