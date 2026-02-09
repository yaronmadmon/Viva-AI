"""
Dissertation Generator v2 -- Multi-Pass, Subsection-Level, PhD-Quality

This replaces the single-call-per-section approach with:
  1.  Plan-first: DissertationPlanner creates subsection outline
  2.  Per-subsection paper search: targeted queries for each subsection
  3.  Multi-pass generation: each subsection gets its own API call (2000-4000 words)
  4.  Cross-section coherence: argument threads woven across sections
  5.  Citation verification: every (Author, Year) checked against paper DB
  6.  Synthetic results: internally-consistent data for Results chapter
  7.  Figure generation: matplotlib charts embedded as base64 PNGs

Target output: 50 000 – 80 000 words of fully AI-generated academic prose.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.ai.academic_search import AcademicPaper, search_academic_papers
from src.ai.dissertation_planner import (
    DissertationPlan,
    SectionMode,
    SectionPlan,
    SubsectionPlan,
    generate_plan,
)
from src.config import get_settings

logger = logging.getLogger(__name__)

# Max papers to include in a single subsection prompt
MAX_PAPERS_PER_SUBSECTION = 15
# Minimum words we expect per subsection (below = retry or expand)
MIN_WORDS_PER_SUBSECTION = 800


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class GeneratedSubsection:
    """One generated subsection."""
    title: str
    content: str
    word_count: int
    papers_cited: List[str]   # (Author, Year) strings found in text
    mode: SectionMode
    verified_citations: int = 0
    hallucinated_citations: int = 0


@dataclass
class GeneratedSection:
    """One generated section (chapter) composed of subsections."""
    title: str
    artifact_type: str
    content: str
    word_count: int
    papers_used: int
    mode: SectionMode
    subsections: List[GeneratedSubsection] = field(default_factory=list)


@dataclass
class GeneratedDissertation:
    """Complete generated dissertation."""
    topic: str
    discipline: str
    sections: List[GeneratedSection]
    total_papers: int
    total_words: int
    papers: List[AcademicPaper]
    verified_citations: int = 0
    hallucinated_citations: int = 0
    student_input_sections: List[str] = field(default_factory=list)


# ── Paper management ─────────────────────────────────────────────────

class PaperPool:
    """Manages the pool of academic papers, supporting per-subsection search."""

    def __init__(self):
        self._papers: Dict[str, AcademicPaper] = {}  # key = normalized title
        self._by_author: Dict[str, List[AcademicPaper]] = {}

    @property
    def all_papers(self) -> List[AcademicPaper]:
        return list(self._papers.values())

    @property
    def count(self) -> int:
        return len(self._papers)

    def add_papers(self, papers: List[AcademicPaper]):
        for p in papers:
            key = self._normalize_title(p.title)
            if key not in self._papers:
                self._papers[key] = p
                for author in p.authors:
                    surname = author.split()[-1].lower() if author else ""
                    if surname:
                        self._by_author.setdefault(surname, []).append(p)

    def find_by_author_year(self, author_surname: str, year: str) -> Optional[AcademicPaper]:
        """Try to find a paper matching an (Author, Year) citation."""
        surname = author_surname.lower().strip()
        year_int = int(year) if year.isdigit() else None

        candidates = self._by_author.get(surname, [])
        for p in candidates:
            if year_int and p.year == year_int:
                return p
        return None

    def get_papers_for_query(self, query: str, max_results: int = 15) -> List[AcademicPaper]:
        """Return papers most relevant to a query (simple keyword match)."""
        if not query.strip():
            return list(self._papers.values())[:max_results]

        keywords = set(query.lower().split())
        scored: List[Tuple[float, AcademicPaper]] = []
        for p in self._papers.values():
            text = f"{p.title} {p.abstract or ''} {' '.join(p.fields)}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                # Boost by citations
                score += min(p.citation_count / 1000, 2.0)
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:max_results]]

    @staticmethod
    def _normalize_title(title: str) -> str:
        return re.sub(r"[^a-z0-9]", "", title.lower())[:100]


# ── Generation engine ────────────────────────────────────────────────

def _build_papers_context(papers: List[AcademicPaper], max_papers: int = 15) -> str:
    """Build a text block of paper summaries for the prompt."""
    lines = []
    for i, p in enumerate(papers[:max_papers], 1):
        cite = p.short_cite
        abstract_snippet = ""
        if p.abstract:
            words = p.abstract.split()[:100]
            abstract_snippet = " ".join(words)
            if len(p.abstract.split()) > 100:
                abstract_snippet += "..."
        journal_str = f" Published in: {p.journal}." if p.journal else ""
        cited = f" Cited {p.citation_count} times." if p.citation_count else ""
        lines.append(
            f"[{i}] {cite}: \"{p.title}\"{journal_str}{cited}\n"
            f"    Abstract: {abstract_snippet or '(not available)'}"
        )
    return "\n\n".join(lines) if lines else "(No papers available for this subsection)"


def _build_system_prompt(discipline: str) -> str:
    """The master system prompt for all generation calls."""
    return (
        "You are a world-class academic researcher writing a PhD dissertation "
        "that would pass examination at a top-tier university (Harvard, Oxford, "
        "Cambridge). You write rigorous, publication-quality academic prose.\n\n"

        "ABSOLUTE RULES:\n"
        "1. Write ONLY flowing academic paragraphs. Never use bullet points or "
        "numbered lists in the main prose (tables are acceptable where noted).\n"
        "2. Every factual claim MUST cite (Author, Year) from the provided papers.\n"
        "3. NEVER fabricate citations. Only cite papers from the provided list.\n"
        "4. When synthetic results data is provided, use those EXACT numbers in "
        "your prose and tables to ensure internal consistency.\n"
        "5. Generate complete, substantive content for every section — no "
        "placeholders, templates, or markers for student input.\n\n"

        "CLAIM DISCIPLINE (Harvard examiners are extremely sensitive to this):\n"
        "- DESCRIPTIVE claims (reporting facts): require citations.\n"
        "- INFERENTIAL claims (drawing conclusions): MUST use hedging — "
        "'suggests', 'indicates', 'appears to', 'may'. NEVER 'proves', "
        "'demonstrates conclusively', 'establishes beyond doubt'.\n"
        "- SPECULATIVE claims (projecting beyond evidence): MUST include "
        "explicit scope limitations and future-research framing.\n"
        "- Never claim generalizability beyond the stated sample/population.\n"
        "- Distinguish statistical significance from practical significance.\n\n"

        "INTELLECTUAL DEPTH:\n"
        "- When discussing prior work, do not just report — EVALUATE. Note "
        "strengths, weaknesses, sample sizes, and methodological limitations.\n"
        "- When presenting disagreements, explain WHY the disagreement exists "
        "(different methods, populations, definitions, theoretical commitments).\n"
        "- Every paragraph should advance the argument, not repeat.\n\n"

        "STYLE:\n"
        "- Write at PhD level: sophisticated vocabulary, complex sentence "
        "structures, proper academic register.\n"
        "- Use transitions between paragraphs that show logical progression.\n"
        "- The writing must be indistinguishable from a real PhD dissertation.\n"
        "- Use section headings (### level) for subsection titles.\n"
        "- Aim for SUBSTANCE over length. Every sentence must earn its place."
    )


async def _generate_subsection(
    topic: str,
    description: str,
    discipline: str,
    section_title: str,
    subsection: SubsectionPlan,
    papers: List[AcademicPaper],
    all_section_titles: List[str],
    prior_context: str,
    argument_thread_descriptions: List[str],
    results_context: str = "",
) -> str:
    """Generate one subsection using OpenAI."""
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder:
        return _stub_subsection(subsection, papers)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)

    papers_context = _build_papers_context(papers, MAX_PAPERS_PER_SUBSECTION)
    system_prompt = _build_system_prompt(discipline)

    # Build thread context
    thread_text = ""
    if argument_thread_descriptions:
        thread_text = (
            "\n\nARGUMENT THREADS that must be visible in this subsection:\n"
            + "\n".join(f"- {t}" for t in argument_thread_descriptions)
        )

    # Build prior context (what has been written so far)
    prior_text = ""
    if prior_context:
        # Only include the last ~2000 words for context window management
        words = prior_context.split()
        if len(words) > 2000:
            prior_text = (
                "\n\nPREVIOUS CONTENT (last ~2000 words for continuity):\n"
                "...\n" + " ".join(words[-2000:])
            )
        else:
            prior_text = f"\n\nPREVIOUS CONTENT (for continuity):\n{prior_context}"

    # Mode instruction: all sections are fully AI-generated
    mode_instruction = ""

    # Inject synthetic results context for Results/Discussion sections
    results_text = ""
    if results_context:
        results_text = f"\n\n{results_context}"

    user_prompt = f"""Write the "{subsection.title}" subsection of the "{section_title}" chapter.

DISSERTATION TOPIC: {topic}
DESCRIPTION: {description}
DISCIPLINE: {discipline}
FULL DISSERTATION STRUCTURE: {', '.join(all_section_titles)}
CURRENT CHAPTER: {section_title}

TARGET LENGTH: {subsection.target_words} words (write AT LEAST this many words with substance)

SPECIFIC INSTRUCTION:
{subsection.instruction}
{thread_text}
{mode_instruction}

REAL ACADEMIC PAPERS TO CITE (cite ONLY these — do NOT invent citations):
{papers_context}
{prior_text}
{results_text}

Write the full subsection now. Start with "### {subsection.title}" and write
comprehensive PhD-quality content. Every paragraph must advance the argument.
Do NOT pad with repetition. Aim for {subsection.target_words}+ words of SUBSTANCE."""

    # Use GPT-4o for all sections
    model = "gpt-4o"

    # Calculate max tokens based on target words (~1.3 tokens per word)
    max_tokens = min(16384, max(4096, int(subsection.target_words * 1.5)))

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        content = (response.choices[0].message.content or "").strip()

        word_count = len(content.split())
        logger.info(
            "  Subsection '%s' generated: %d words (target: %d) [%s]",
            subsection.title, word_count, subsection.target_words, model,
        )

        # Multi-pass expansion: keep expanding until we're within 75% of target
        expansion_pass = 0
        while (
            len(content.split()) < subsection.target_words * 0.75
            and len(content.split()) > 200
            and expansion_pass < 3  # max 3 expansion passes
        ):
            expansion_pass += 1
            word_count = len(content.split())
            logger.info("  Expanding '%s' pass %d (only %d/%d words)...",
                        subsection.title, expansion_pass,
                        word_count, subsection.target_words)
            content = await _expand_subsection(
                client, model, system_prompt, content,
                subsection, papers_context, topic,
            )

        if content:
            return content
    except Exception as exc:
        logger.error("OpenAI generation failed for '%s': %s", subsection.title, exc)

    return _stub_subsection(subsection, papers)


async def _expand_subsection(
    client,
    model: str,
    system_prompt: str,
    existing_content: str,
    subsection: SubsectionPlan,
    papers_context: str,
    topic: str,
) -> str:
    """Expand an under-length subsection with a follow-up call."""
    remaining_words = subsection.target_words - len(existing_content.split())

    prompt = f"""The following subsection of a PhD dissertation is too short. 
Expand it with additional SUBSTANTIVE content — deeper analysis, more citations, 
more nuanced discussion. Do NOT repeat what's already written.

TOPIC: {topic}
SUBSECTION: {subsection.title}
TARGET: Add approximately {remaining_words} more words of substance.

EXISTING CONTENT:
{existing_content}

PAPERS AVAILABLE TO CITE:
{papers_context}

INSTRUCTION: Continue writing from where the existing content ends. Maintain 
the same academic tone, add new arguments, cite additional papers, deepen 
the analysis. Start your continuation WITHOUT repeating the heading."""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=min(8192, max(2048, int(remaining_words * 1.5))),
            temperature=0.7,
        )
        continuation = (response.choices[0].message.content or "").strip()
        if continuation:
            combined = existing_content + "\n\n" + continuation
            logger.info("  Expanded to %d words", len(combined.split()))
            return combined
    except Exception as exc:
        logger.warning("Expansion failed for '%s': %s", subsection.title, exc)

    return existing_content


def _stub_subsection(subsection: SubsectionPlan, papers: List[AcademicPaper]) -> str:
    """Fallback stub when no API key is available."""
    lines = [f"### {subsection.title}\n"]
    lines.append(
        f"[This subsection targets {subsection.target_words} words. "
        f"Configure OPENAI_API_KEY to generate full PhD-level content.]\n"
    )
    if papers:
        lines.append(f"Available papers for this subsection: {len(papers)}")
        for p in papers[:5]:
            lines.append(f"- {p.short_cite}: \"{p.title}\"")
    return "\n".join(lines)


# ── Citation verification ────────────────────────────────────────────

_CITE_PATTERN = re.compile(
    r"\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&\s*[A-Z][a-z]+))?),?\s*(\d{4})\)"
)


def extract_citations(text: str) -> List[Tuple[str, str]]:
    """Extract all (Author, Year) citations from text."""
    return _CITE_PATTERN.findall(text)


def verify_citations(
    text: str,
    paper_pool: PaperPool,
) -> Tuple[int, int, List[str]]:
    """
    Verify every citation in text against the paper pool.

    Returns:
        (verified_count, hallucinated_count, list of hallucinated citations)
    """
    citations = extract_citations(text)
    verified = 0
    hallucinated = 0
    hallucinated_list = []

    seen = set()
    for author, year in citations:
        key = f"{author}_{year}"
        if key in seen:
            continue
        seen.add(key)

        # Extract surname
        surname = author.split()[0]  # "Smith" or "Smith" from "Smith et al."
        paper = paper_pool.find_by_author_year(surname, year)
        if paper:
            verified += 1
        else:
            hallucinated += 1
            hallucinated_list.append(f"({author}, {year})")

    return verified, hallucinated, hallucinated_list


# ── References builder ───────────────────────────────────────────────

def _build_references_section(papers: List[AcademicPaper], text: str) -> str:
    """Build references section using ONLY papers that were actually cited."""
    cited = extract_citations(text)
    cited_surnames = {author.split()[0].lower() for author, _ in cited}
    cited_years = {year for _, year in cited}

    # Filter to papers actually cited
    referenced = []
    for p in papers:
        for author in p.authors:
            parts = author.split() if author else []
            surname = parts[-1].lower() if parts else ""
            if surname and surname in cited_surnames and str(p.year) in cited_years:
                referenced.append(p)
                break

    # Sort alphabetically by first author surname
    def _sort_key(p: AcademicPaper) -> str:
        if not p.authors:
            return ""
        parts = p.authors[0].split() if p.authors[0] else []
        return parts[-1].lower() if parts else ""

    referenced.sort(key=_sort_key)

    # Deduplicate
    seen = set()
    unique_refs = []
    for p in referenced:
        key = (p.title.lower()[:80], p.year)
        if key not in seen:
            seen.add(key)
            unique_refs.append(p)

    lines = ["## References\n"]
    for p in unique_refs:
        lines.append(p.apa_reference)
        lines.append("")

    if not unique_refs:
        lines.append("*No verified references found. Ensure papers are properly cited.*\n")

    return "\n".join(lines)


# ── Main pipeline ────────────────────────────────────────────────────

async def generate_dissertation(
    topic: str,
    description: str,
    discipline: str,
) -> GeneratedDissertation:
    """
    Generate a complete PhD dissertation using multi-pass, subsection-level
    generation with targeted paper search and citation verification.

    Pipeline:
      1. Create plan (subsection outline + argument threads)
      2. Search papers per subsection (targeted queries)
      3. Generate each subsection individually
      4. Verify citations against paper pool
      5. Build references from actually-cited papers

    Target: 50 000+ words, 100+ real citations, all claims grounded.
    """
    logger.info("="*60)
    logger.info("DISSERTATION GENERATION v2 STARTING")
    logger.info("Topic: %s", topic)
    logger.info("Discipline: %s", discipline)
    logger.info("="*60)

    # ── Step 1: Create plan ──────────────────────────────────────
    logger.info("Step 1: Creating dissertation plan...")
    plan = await generate_plan(topic, description, discipline)
    logger.info(
        "Plan: %d sections, %d subsections, target %d words",
        len(plan.sections),
        sum(len(s.subsections) for s in plan.sections),
        plan.total_target_words,
    )

    # ── Step 2: Search papers per subsection ─────────────────────
    logger.info("Step 2: Searching academic papers...")
    paper_pool = PaperPool()

    # First, a broad search
    broad_query = f"{topic} {description or ''}"[:200]
    broad_papers = await search_academic_papers(broad_query, max_results=60)
    paper_pool.add_papers(broad_papers)
    logger.info("  Broad search: %d papers", len(broad_papers))

    # Then, targeted searches per subsection (batch for speed)
    unique_queries = plan.all_search_queries
    logger.info("  Running %d targeted searches...", len(unique_queries))

    # Run searches in batches of 5 to respect rate limits
    for batch_start in range(0, len(unique_queries), 5):
        batch = unique_queries[batch_start:batch_start + 5]
        results = await asyncio.gather(
            *(search_academic_papers(q, max_results=20) for q in batch),
            return_exceptions=True,
        )
        for q, r in zip(batch, results):
            if isinstance(r, list):
                paper_pool.add_papers(r)
                logger.info("    '%s...': %d papers", q[:40], len(r))
            else:
                logger.warning("    Search failed for '%s': %s", q[:40], r)

        # Small delay between batches
        if batch_start + 5 < len(unique_queries):
            await asyncio.sleep(1)

    logger.info("  Total unique papers: %d", paper_pool.count)

    # ── Step 3: Generate each subsection ─────────────────────────
    logger.info("Step 3: Generating dissertation content...")

    from src.ai.results_generator import generate_synthetic_results, SyntheticResults
    from src.ai.figure_generator import plan_figures, generate_all_figures

    all_section_titles = [s.title for s in plan.sections]
    generated_sections: List[GeneratedSection] = []
    all_generated_text = ""  # running text for coherence
    student_input_sections: List[str] = []

    # Track methodology text and research questions for synthetic results
    methodology_text = ""
    research_questions: List[str] = []
    synthetic_results: Optional[SyntheticResults] = None
    results_context_str = ""

    for section_plan in plan.sections:
        logger.info("  Chapter: %s (%d subsections, target %d words)",
                     section_plan.title, len(section_plan.subsections),
                     section_plan.target_words)

        # After Methodology is done, generate synthetic results before Results
        if section_plan.title == "Results" and synthetic_results is None:
            logger.info("  Generating synthetic results data...")
            # Extract research questions from argument threads
            rq_thread = next(
                (t for t in plan.argument_threads if t.id == "research_questions"),
                None,
            )
            if rq_thread:
                research_questions = [rq_thread.description]

            synthetic_results = await generate_synthetic_results(
                topic=topic,
                methodology_text=methodology_text,
                research_questions=research_questions,
            )
            results_context_str = synthetic_results.as_context_string()
            logger.info("  Synthetic results ready (%d models, %d tests)",
                         len(synthetic_results.model_metrics),
                         len(synthetic_results.statistical_tests))

        section_content_parts = [f"## {section_plan.title}\n"]
        section_subsections: List[GeneratedSubsection] = []
        section_word_count = 0

        for sub in section_plan.subsections:
            # Special handling for references
            if sub.instruction == "SPECIAL:REFERENCES":
                continue

            # Get papers relevant to this subsection
            sub_papers = paper_pool.get_papers_for_query(
                sub.search_query, MAX_PAPERS_PER_SUBSECTION
            )

            # Build argument thread descriptions
            thread_descs = []
            for thread in plan.argument_threads:
                if thread.id in sub.argument_threads:
                    thread_descs.append(thread.description)

            # Pass synthetic results context for Results and Discussion sections
            sub_results_ctx = ""
            if section_plan.title in ("Results", "Discussion") and results_context_str:
                sub_results_ctx = results_context_str

            # Generate
            content = await _generate_subsection(
                topic=topic,
                description=description,
                discipline=discipline,
                section_title=section_plan.title,
                subsection=sub,
                papers=sub_papers,
                all_section_titles=all_section_titles,
                prior_context=all_generated_text[-8000:] if all_generated_text else "",
                argument_thread_descriptions=thread_descs,
                results_context=sub_results_ctx,
            )

            wc = len(content.split())
            section_word_count += wc

            # Extract citations for verification
            cited = extract_citations(content)
            cited_strs = [f"({a}, {y})" for a, y in cited]

            section_subsections.append(GeneratedSubsection(
                title=sub.title,
                content=content,
                word_count=wc,
                papers_cited=cited_strs,
                mode=sub.mode,
            ))

            section_content_parts.append(content)
            all_generated_text += "\n\n" + content

            # Small delay between subsections to respect rate limits
            await asyncio.sleep(0.5)

        # Track methodology text for synthetic results generation
        if section_plan.title == "Methodology":
            methodology_text = "\n\n".join(section_content_parts)

        # After Results is fully generated, create and embed figures
        if section_plan.title == "Results" and synthetic_results is not None:
            logger.info("  Generating figures...")
            try:
                figure_specs = await plan_figures(topic, synthetic_results.raw_json)
                figures = generate_all_figures(figure_specs)
                if figures:
                    # Append figures to the last subsection content
                    figure_md_parts = ["\n\n---\n\n### Figures\n"]
                    for fig in figures:
                        figure_md_parts.append(f"\n{fig.markdown}\n")
                        figure_md_parts.append(
                            f"\n*Figure {fig.figure_number}: {fig.caption}*\n"
                        )
                    figure_block = "\n".join(figure_md_parts)
                    section_content_parts.append(figure_block)
                    section_word_count += len(figure_block.split())
                    logger.info("  Embedded %d figures into Results", len(figures))
            except Exception as exc:
                logger.error("Figure generation failed: %s", exc)

        # Handle references section
        if section_plan.title in ("References", "Bibliography", "Table of Authorities"):
            ref_content = _build_references_section(
                paper_pool.all_papers, all_generated_text
            )
            section_content_parts = [ref_content]
            section_word_count = len(ref_content.split())

        # Assemble section
        full_section_content = "\n\n".join(section_content_parts)

        generated_sections.append(GeneratedSection(
            title=section_plan.title,
            artifact_type=section_plan.artifact_type,
            content=full_section_content,
            word_count=section_word_count,
            papers_used=paper_pool.count,
            mode=section_plan.mode,
            subsections=section_subsections,
        ))

        logger.info("    → %s: %d words", section_plan.title, section_word_count)

    # ── Step 4: Citation verification ────────────────────────────
    logger.info("Step 4: Verifying citations...")
    total_verified = 0
    total_hallucinated = 0
    all_hallucinated: List[str] = []

    for section in generated_sections:
        v, h, h_list = verify_citations(section.content, paper_pool)
        total_verified += v
        total_hallucinated += h
        all_hallucinated.extend(h_list)
        for sub in section.subsections:
            sv, sh, _ = verify_citations(sub.content, paper_pool)
            sub.verified_citations = sv
            sub.hallucinated_citations = sh

    logger.info("  Verified: %d, Hallucinated: %d", total_verified, total_hallucinated)
    if all_hallucinated:
        logger.warning("  Hallucinated citations: %s", ", ".join(all_hallucinated[:10]))

    # ── Step 5: Assemble result ──────────────────────────────────
    total_words = sum(s.word_count for s in generated_sections)

    result = GeneratedDissertation(
        topic=topic,
        discipline=discipline,
        sections=generated_sections,
        total_papers=paper_pool.count,
        total_words=total_words,
        papers=paper_pool.all_papers,
        verified_citations=total_verified,
        hallucinated_citations=total_hallucinated,
        student_input_sections=[],  # all sections are fully AI-generated
    )

    logger.info("="*60)
    logger.info("GENERATION COMPLETE")
    logger.info("  Total words: %d", total_words)
    logger.info("  Total papers: %d", paper_pool.count)
    logger.info("  Verified citations: %d", total_verified)
    logger.info("  Hallucinated citations: %d", total_hallucinated)
    logger.info("="*60)

    return result
