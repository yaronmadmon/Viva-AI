"""
Project endpoints.
"""

import asyncio
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload

from src.api.deps import (
    DbSession,
    CurrentUser,
    RequireProjectView,
    RequireProjectEdit,
    get_client_ip,
)
from src.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectShareRequest,
    CollaboratorResponse,
    ProjectStatsResponse,
    DocumentChunk,
    ProjectDocumentResponse,
)
from src.schemas.common import SuccessResponse, PaginatedResponse
from src.kernel.models.project import ResearchProject, ProjectShare, ProjectStatus
from src.kernel.models.artifact import Artifact, ArtifactType, ArtifactVersion, ContributionCategory, compute_content_hash
from src.kernel.models.user import User
from src.kernel.models.event_log import EventType
from src.kernel.events.event_store import EventStore
from src.kernel.permissions.permission_service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter()


def _enum_val(e):
    """Safely get enum value (SQLite may return str)."""
    return e.value if hasattr(e, "value") else e


# ----- Dissertation scaffold templates per discipline -----
# Each entry: (title, artifact_type, rich starter content)

_SCAFFOLD_SECTIONS = {
    "stem": [
        ("Introduction", "section", """## Introduction

### Background
Provide context for your research area. What is the broader field, and why does it matter?

### Problem Statement
Clearly define the specific problem or gap in knowledge that your research addresses.

### Research Objectives
1. Primary objective: [State the main goal of your research]
2. Secondary objectives:
   - [Objective 2]
   - [Objective 3]

### Research Questions / Hypotheses
- RQ1: [Your primary research question]
- H1: [Your hypothesis, if applicable]

### Significance of the Study
Explain why this research is important. Who benefits from the findings? What practical or theoretical contributions does it make?

### Scope and Limitations
Define the boundaries of your study. What will you include and exclude, and why?
"""),
        ("Literature Review", "section", """## Literature Review

### Overview
This section surveys the existing body of knowledge relevant to your research topic. Organize the review thematically or chronologically.

### Key Themes

#### Theme 1: [Name]
Summarize the relevant literature for this theme. Identify key authors, findings, and methodologies.

- Author et al. (Year) found that...
- This was supported by Author (Year), who demonstrated...

#### Theme 2: [Name]
Continue reviewing literature under the next theme.

#### Theme 3: [Name]
Continue as needed.

### Research Gap
Based on the literature reviewed above, clearly identify the gap that your research aims to fill. What has not been studied? What contradictions exist? What methodological improvements are needed?

### Conceptual / Theoretical Framework
Describe the theoretical lens through which you approach this problem. Include a diagram if helpful.
"""),
        ("Methodology", "method", """## Methodology

### Research Design
Describe your overall approach (experimental, quasi-experimental, simulation, computational, etc.).

### Materials and Equipment
List the key materials, software, instruments, or datasets you will use.

| Item | Description | Source |
|------|-------------|--------|
| [Material 1] | [Description] | [Source] |
| [Material 2] | [Description] | [Source] |

### Data Collection
Explain how you will collect or generate your data. Include:
- Sample size and selection criteria
- Variables (independent, dependent, controlled)
- Measurement instruments and their validity

### Experimental Procedure
Describe the step-by-step procedure of your experiment or study:
1. Step 1: [Description]
2. Step 2: [Description]
3. Step 3: [Description]

### Data Analysis
Describe the statistical or analytical methods you will use to process and interpret your data.

### Ethical Considerations
Address any ethical concerns (IRB approval, informed consent, data privacy, etc.).
"""),
        ("Results", "result", """## Results

### Overview
Summarize the key findings of your study before presenting detailed results.

### Finding 1: [Title]
Present your first major finding with supporting data. Include tables, figures, or charts as needed.

**Table 1: [Description]**
| Variable | Group A | Group B | p-value |
|----------|---------|---------|---------|
| [Var 1]  | [Value] | [Value] | [Value] |

### Finding 2: [Title]
Present the next finding with supporting evidence.

### Finding 3: [Title]
Continue as needed.

### Summary of Results
Provide a brief overview of how the results relate to your research questions and hypotheses.
"""),
        ("Discussion", "discussion", """## Discussion

### Interpretation of Results
Explain what your results mean in the context of your research questions. How do they answer or address your hypotheses?

### Comparison with Existing Literature
Compare your findings with those of previous studies. Where do your results agree or disagree?

- Your finding on [topic] aligns with Author (Year), who also found...
- In contrast to Author (Year), your results suggest...

### Implications
Discuss the practical and theoretical implications of your findings.

#### Theoretical Implications
What does this contribute to the field's understanding?

#### Practical Implications
How can practitioners, engineers, or policymakers use these findings?

### Limitations
Acknowledge the limitations of your study honestly:
1. [Limitation 1 and its potential impact on results]
2. [Limitation 2 and its potential impact on results]

### Future Research Directions
Suggest specific areas for future investigation based on your findings and limitations.
"""),
        ("Conclusion", "section", """## Conclusion

### Summary of Key Findings
Restate the most important results of your study in clear, concise terms:
1. [Key finding 1]
2. [Key finding 2]
3. [Key finding 3]

### Contributions
Summarize the original contributions this research makes to the field.

### Recommendations
Based on your findings, provide actionable recommendations for researchers, practitioners, or policymakers.

### Final Remarks
End with a brief statement about the broader significance of your work and the direction of future research.
"""),
        ("References", "source", """## References

Use the citation format required by your institution or field (e.g., IEEE, APA, Vancouver).

### How to organize your references:
- List all sources cited in the text
- Arrange alphabetically by first author's surname (or numerically if using numbered citations)
- Ensure every in-text citation has a corresponding reference entry and vice versa

### Example entries:

[1] A. Author, B. Author, and C. Author, "Title of the article," *Journal Name*, vol. X, no. Y, pp. 1-10, Year. doi: 10.xxxx/xxxxx

[2] D. Author, *Title of Book*, Edition. City: Publisher, Year.

---
*Start adding your references below:*

"""),
    ],
    "humanities": [
        ("Introduction", "section", """## Introduction

### Opening
Begin with an engaging entry point into your topic: an anecdote, a provocative question, a key quote, or a striking observation that frames the significance of your inquiry.

### Research Context
Situate your topic within its broader intellectual, cultural, or historical context. Why does this subject matter now?

### Thesis Statement
State your central argument clearly and precisely. This is the claim your entire dissertation will develop and defend.

> **Thesis:** [Write your thesis statement here]

### Research Questions
- RQ1: [Your primary research question]
- RQ2: [Secondary question]
- RQ3: [Secondary question]

### Scope and Structure
Briefly outline the scope of your argument and provide a roadmap of the chapters/sections that follow.

### Methodological Approach
Describe the interpretive or analytical methods you will employ (close reading, discourse analysis, archival research, comparative analysis, etc.).
"""),
        ("Theoretical Framework", "section", """## Theoretical Framework

### Overview
Identify the critical theories, philosophical traditions, or conceptual frameworks that inform your analysis.

### Primary Framework: [Name]
Describe the main theoretical lens you are using. Who are its key thinkers? What are its central concepts?

- Key concept 1: [Definition and relevance to your work]
- Key concept 2: [Definition and relevance to your work]

### Secondary Framework: [Name]
If applicable, describe additional theories that complement your primary framework.

### Application to Your Research
Explain specifically how these frameworks will be applied to your primary sources or case studies. How do they help you see something new or different?

### Critical Assessment
Acknowledge any limitations or criticisms of your chosen frameworks and explain why they remain useful for your purposes.
"""),
        ("Literature Review", "section", """## Literature Review

### Introduction
Explain the scope and purpose of this review. How is it organized?

### Scholarly Conversation 1: [Theme]
Survey the key scholars and works addressing this theme. Identify points of agreement, disagreement, and evolution over time.

### Scholarly Conversation 2: [Theme]
Continue with the next thematic grouping.

### Scholarly Conversation 3: [Theme]
Continue as needed.

### Positioning Your Contribution
Clearly articulate where your work fits within the existing scholarship. What conversation are you entering? What new perspective, evidence, or argument do you bring?
"""),
        ("Analysis", "section", """## Analysis

### Introduction
Briefly introduce the primary sources, texts, or cases you will analyze and the approach you will take.

### Analysis of [Source/Text/Case 1]
Provide your close reading, interpretation, or critical analysis. Support your claims with specific evidence (quotations, examples, data).

### Analysis of [Source/Text/Case 2]
Continue your analysis with the next source or case.

### Analysis of [Source/Text/Case 3]
Continue as needed.

### Synthesis
Draw connections across your analyses. What patterns, themes, or tensions emerge?
"""),
        ("Discussion", "discussion", """## Discussion

### Developing the Argument
Bring together the threads of your analysis to develop your central argument. How do the individual analyses collectively support your thesis?

### Addressing Counterarguments
Acknowledge and respond to the strongest counterarguments or alternative interpretations. Why is your reading more persuasive or productive?

### Broader Implications
What does your argument contribute to the larger scholarly conversation? How does it change how we understand the topic?

### Connections to Contemporary Debates
If relevant, connect your findings to current cultural, political, or intellectual debates.
"""),
        ("Conclusion", "section", """## Conclusion

### Restating the Argument
Restate your thesis and summarize how your analysis has supported it, without simply repeating earlier sections.

### Original Contributions
Articulate clearly what is new about your work: new readings, new evidence, new theoretical connections.

### Limitations and Open Questions
Acknowledge what your study could not address and pose questions for future scholarship.

### Closing Reflection
End with a broader reflection on the significance of your work and its implications beyond the academy.
"""),
        ("Bibliography", "source", """## Bibliography

Use the citation style required by your discipline (e.g., MLA, Chicago, Harvard).

### Primary Sources
List the primary texts, archives, artworks, or original materials you have analyzed.

### Secondary Sources
List all scholarly works cited in your text.

---
*Start adding your sources below:*

"""),
    ],
    "social_sciences": [
        ("Introduction", "section", """## Introduction

### Background and Context
Provide the broader context for your research. What social phenomenon, policy issue, or behavioral pattern are you investigating? Why is it important?

### Problem Statement
Clearly define the specific problem your research addresses. What do we not yet understand?

### Purpose of the Study
State the purpose of your research in one or two sentences:

> The purpose of this study is to [examine/explore/investigate] the relationship between [variable A] and [variable B] among [population], in order to [expected contribution].

### Research Questions
- RQ1: [Primary research question]
- RQ2: [Secondary research question]

### Hypotheses (if applicable)
- H1: [Hypothesis derived from RQ1]
- H2: [Hypothesis derived from RQ2]

### Significance of the Study
Explain who will benefit from this research and how: policymakers, educators, practitioners, affected communities, etc.

### Definition of Key Terms
Define the central concepts and variables used in your study to ensure clarity.

| Term | Definition |
|------|-----------|
| [Term 1] | [Your operational definition] |
| [Term 2] | [Your operational definition] |
"""),
        ("Literature Review", "section", """## Literature Review

### Introduction
Explain the scope and organization of this review.

### Theoretical Foundation
Describe the theory or theories underpinning your study. Key theorists, core propositions, and how they relate to your variables.

### Theme 1: [Name]
Review empirical studies related to this theme. For each study, note the authors, methods, sample, key findings, and limitations.

### Theme 2: [Name]
Continue reviewing literature under the next theme.

### Theme 3: [Name]
Continue as needed.

### Summary and Research Gap
Synthesize the reviewed literature and clearly identify the gap your study fills. What questions remain unanswered? What populations are understudied? What methodological improvements are needed?
"""),
        ("Methodology", "method", """## Methodology

### Research Design
Describe your overall design (quantitative, qualitative, mixed methods) and justify your choice.

### Population and Sampling
- **Target population:** [Describe]
- **Sampling method:** [Probability/non-probability, specific technique]
- **Sample size:** [Number and justification]
- **Inclusion/exclusion criteria:** [List criteria]

### Data Collection Instruments
Describe the instruments you will use (surveys, interview guides, observation protocols, etc.):

| Instrument | Purpose | Validity/Reliability |
|-----------|---------|---------------------|
| [Instrument 1] | [Purpose] | [Evidence] |
| [Instrument 2] | [Purpose] | [Evidence] |

### Data Collection Procedure
Describe the step-by-step process of gathering your data, including timeline and setting.

### Data Analysis Plan
- **Quantitative:** Describe statistical tests (e.g., regression, t-test, ANOVA) and software (SPSS, R, etc.)
- **Qualitative:** Describe coding approach (thematic analysis, grounded theory, etc.) and software (NVivo, Atlas.ti, etc.)

### Ethical Considerations
Address IRB approval, informed consent, confidentiality, and any risks to participants.

### Limitations of the Method
Acknowledge methodological limitations upfront.
"""),
        ("Results", "result", """## Results

### Overview
Summarize your key findings before presenting details.

### Descriptive Statistics / Participant Demographics
Present demographic information and descriptive statistics for your sample.

| Characteristic | n | % |
|---------------|---|---|
| [Category 1] | [n] | [%] |
| [Category 2] | [n] | [%] |

### Finding 1: [Research Question / Hypothesis]
Present the results that address your first research question. Include tables, figures, and effect sizes.

### Finding 2: [Research Question / Hypothesis]
Present results for the next research question.

### Finding 3: [Research Question / Hypothesis]
Continue as needed.

### Additional / Unexpected Findings
Report any notable findings that were not directly part of your research questions.
"""),
        ("Discussion", "discussion", """## Discussion

### Summary of Findings
Briefly restate your key findings in non-technical language.

### Interpretation
Explain what your findings mean. How do they answer your research questions?

### Connection to Literature
Compare your results with the studies reviewed in your literature review:
- Finding 1 is consistent with / contradicts Author (Year), who found...
- Finding 2 extends the work of Author (Year) by showing...

### Theoretical Implications
How do your findings contribute to or challenge the theories described in your framework?

### Practical Implications
What actionable recommendations follow from your findings for practitioners, policymakers, or organizations?

### Limitations
Discuss limitations that may affect the interpretation or generalizability of your results:
1. [Limitation and its impact]
2. [Limitation and its impact]

### Recommendations for Future Research
Suggest specific next steps for the field based on your findings and limitations.
"""),
        ("Conclusion", "section", """## Conclusion

### Summary
Provide a concise summary of the entire study: problem, methods, key findings, and implications.

### Key Contributions
State the original contributions this study makes:
1. [Contribution 1]
2. [Contribution 2]

### Final Reflections
Close with a statement about the broader significance of your research for the field and society.
"""),
        ("References", "source", """## References

Use APA 7th Edition format (or the style required by your institution).

### Format examples:

**Journal article:**
Author, A. A., & Author, B. B. (Year). Title of article. *Title of Periodical*, *volume*(issue), page-page. https://doi.org/xxxxx

**Book:**
Author, A. A. (Year). *Title of work: Capital letter also for subtitle*. Publisher. https://doi.org/xxxxx

**Book chapter:**
Author, A. A. (Year). Title of chapter. In E. E. Editor (Ed.), *Title of book* (pp. xx-xx). Publisher.

---
*Start adding your references below:*

"""),
    ],
    "legal": [
        ("Introduction", "section", """## Introduction

### Background
Introduce the legal issue or problem that motivates your research. Provide context for the reader.

### Research Question
State your research question clearly:

> This dissertation examines whether/how [legal issue] in the context of [jurisdiction/area of law].

### Significance
Explain why this legal question matters: implications for rights, policy, judicial practice, or legislative reform.

### Scope and Delimitations
Define what your research covers and what falls outside its scope.

### Methodology
Briefly describe your legal research methodology: doctrinal analysis, comparative law, empirical legal research, law and economics, etc.

### Structure
Provide an overview of the chapters that follow.
"""),
        ("Legal Framework", "section", """## Legal Framework

### Constitutional / Statutory Framework
Outline the relevant constitutional provisions, statutes, and regulations that govern this area of law.

### Key Legislation
| Legislation | Jurisdiction | Relevant Provisions |
|------------|-------------|-------------------|
| [Act/Statute] | [Jurisdiction] | [Sections] |

### Case Law
Summarize the leading cases that have shaped the current legal position:

#### [Case Name] ([Year])
- **Facts:** Brief summary
- **Held:** Key ruling
- **Significance:** Why this case matters for your research

### Regulatory Framework
If applicable, describe relevant regulatory bodies and their guidelines.

### International / Comparative Framework
Outline relevant international treaties, conventions, or comparative legal principles.
"""),
        ("Literature Review", "section", """## Literature Review

### Doctrinal Commentary
Survey the key academic commentary on your legal topic. Identify the dominant views, minority positions, and unresolved debates.

### Critical Perspectives
Review scholarship that critically examines the current legal framework. What reforms have been proposed?

### Interdisciplinary Perspectives
If relevant, review insights from other disciplines (economics, sociology, political science) that inform the legal analysis.

### Gap in the Literature
Identify what has not been adequately addressed in existing scholarship and how your research fills that gap.
"""),
        ("Analysis", "section", """## Analysis

### Analytical Framework
Describe the method of analysis you will employ in this section.

### Analysis of [Issue 1]
Apply the legal framework to your specific research question. Analyze the relevant law, cases, and scholarly arguments.

### Analysis of [Issue 2]
Continue your analysis.

### Analysis of [Issue 3]
Continue as needed.

### Synthesis
Draw together the threads of your analysis to form a coherent legal argument.
"""),
        ("Comparative Perspective", "section", """## Comparative Perspective

### Rationale for Comparison
Explain why a comparative approach is valuable for your research question and which jurisdictions you are comparing.

### Jurisdiction A: [Name]
Describe how this jurisdiction addresses the legal issue. Key legislation, case law, and outcomes.

### Jurisdiction B: [Name]
Describe the approach in this jurisdiction.

### Comparative Analysis
Compare and contrast the approaches. What can be learned from each? Which approach is more effective and why?

### Lessons for [Your Jurisdiction]
What reforms or improvements could be adopted based on the comparative analysis?
"""),
        ("Conclusion & Recommendations", "section", """## Conclusion & Recommendations

### Summary of Findings
Restate the key findings of your legal analysis.

### Recommendations
Based on your analysis, propose specific recommendations:

#### Legislative Recommendations
1. [Recommendation]
2. [Recommendation]

#### Judicial Recommendations
1. [Recommendation]

#### Policy Recommendations
1. [Recommendation]

### Contribution to Legal Scholarship
Summarize the original contribution of your research.

### Closing
End with a reflection on the importance of addressing this legal issue.
"""),
        ("Table of Authorities", "source", """## Table of Authorities

### Cases
List all cases cited, organized alphabetically or by jurisdiction.

| Case | Citation | Jurisdiction |
|------|----------|-------------|
| [Case name] | [Full citation] | [Jurisdiction] |

### Legislation
| Legislation | Citation |
|------------|----------|
| [Act/Statute] | [Full citation] |

### International Instruments
| Instrument | Citation |
|-----------|----------|
| [Treaty/Convention] | [Full citation] |

### Secondary Sources
List all academic articles, books, and reports cited.

---
*Start adding your authorities below:*

"""),
    ],
}

# Fallback / mixed discipline
_SCAFFOLD_SECTIONS["mixed"] = [
    ("Introduction", "section", """## Introduction

### Background
Provide context for your research. What is the broader topic and why is it important?

### Problem Statement
What specific problem or gap in knowledge does your research address?

### Research Objectives
1. [Primary objective]
2. [Secondary objective]
3. [Secondary objective]

### Research Questions
- RQ1: [Your primary research question]
- RQ2: [Secondary question]

### Significance
Explain the importance of this research: who benefits and how.

### Scope
Define what your study covers and its boundaries.
"""),
    ("Literature Review", "section", """## Literature Review

### Overview
This section reviews the existing research relevant to your topic.

### Theme 1: [Name]
Survey the key works, findings, and debates under this theme.

### Theme 2: [Name]
Continue with the next theme.

### Theme 3: [Name]
Continue as needed.

### Research Gap
Based on the literature above, identify the specific gap your research addresses.
"""),
    ("Methodology", "method", """## Methodology

### Research Design
Describe your overall approach and justify your choice.

### Data Sources
Explain what data you will collect or use, and from where.

### Methods
Detail the specific methods for data collection and analysis.

### Ethical Considerations
Address any ethical issues relevant to your research.

### Limitations
Acknowledge methodological limitations.
"""),
    ("Results / Analysis", "result", """## Results / Analysis

### Overview
Summarize your key findings before presenting details.

### Finding 1: [Title]
Present your first major finding with supporting evidence.

### Finding 2: [Title]
Present the next finding.

### Finding 3: [Title]
Continue as needed.

### Summary
Provide a brief synthesis of all findings.
"""),
    ("Discussion", "discussion", """## Discussion

### Interpretation
Explain what your findings mean in the context of your research questions.

### Connection to Literature
Compare your results with existing studies.

### Implications
Discuss practical and theoretical implications.

### Limitations
Acknowledge limitations that affect interpretation.

### Future Research
Suggest directions for further investigation.
"""),
    ("Conclusion", "section", """## Conclusion

### Summary
Restate the key findings concisely.

### Contributions
Articulate what is new about your work.

### Recommendations
Provide actionable recommendations based on your findings.

### Final Remarks
Close with a reflection on the broader significance of your research.
"""),
    ("References", "source", """## References

Use the citation format required by your institution.

---
*Start adding your references below:*

"""),
]


async def _scaffold_project_structure(
    db,
    project_id,
    user_id,
    discipline_type: str,
) -> int:
    """Create initial dissertation sections for a new project. Returns count created.

    Pre-generates all IDs to avoid multiple flush() calls inside the loop,
    which triggers 'cannot commit transaction - SQL statements in progress'
    on aiosqlite.
    """
    from src.kernel.models.base import generate_uuid

    sections = _SCAFFOLD_SECTIONS.get(discipline_type, _SCAFFOLD_SECTIONS["mixed"])
    count = 0
    for position, (title, artifact_type, placeholder) in enumerate(sections):
        content_hash = compute_content_hash(placeholder)
        art_id = generate_uuid()
        artifact = Artifact(
            id=art_id,
            project_id=project_id,
            artifact_type=artifact_type,
            title=title,
            content=placeholder,
            content_hash=content_hash,
            position=position,
            contribution_category=ContributionCategory.PRIMARILY_HUMAN,
            ai_modification_ratio=1.0,
        )
        db.add(artifact)
        # Create initial version (pre-generated id avoids needing flush per artifact)
        version = ArtifactVersion(
            id=generate_uuid(),
            artifact_id=art_id,
            version_number=1,
            title=title,
            content=placeholder,
            content_hash=content_hash,
            created_by=user_id,
            contribution_category=ContributionCategory.PRIMARILY_HUMAN,
        )
        db.add(version)
        count += 1
    # NOTE: caller is responsible for flushing / committing
    return count


# ---------------------------------------------------------------------------
# Background dissertation generation
# ---------------------------------------------------------------------------

async def _background_generate_dissertation(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    topic: str,
    description: str,
    discipline: str,
):
    """Background task: generate full PhD content and update artifacts.

    Uses the v2 multi-pass generator for real PhD-quality output:
      - Subsection-level planning and generation
      - Per-subsection academic paper search (100+ papers)
      - Citation verification against real paper database
      - Honest section classification (AI vs student-template)
      - Target: 50 000+ words of substantive prose

    Runs with its own DB session (the request session is already closed).
    """
    from src.database import async_session_maker
    from src.ai.dissertation_generator_v2 import generate_dissertation
    from src.kernel.models.base import generate_uuid

    import sys
    logger.info("Background generation v2 starting for project %s", project_id)
    print(f"[BACKGROUND] Generation v2 starting for {project_id}", file=sys.stderr, flush=True)

    try:
        # Step 1: Generate the full dissertation (plan → search → multi-pass write)
        dissertation = await generate_dissertation(
            topic=topic,
            description=description or topic,
            discipline=discipline,
        )
        print(f"[BACKGROUND] Generation complete: {dissertation.total_words} words", file=sys.stderr, flush=True)

        # Step 2: Update each artifact with the generated content
        async with async_session_maker() as db:
            try:
                updated_count = 0
                for section in dissertation.sections:
                    # Find the matching artifact by title
                    query = select(Artifact).where(
                        and_(
                            Artifact.project_id == project_id,
                            Artifact.title == section.title,
                            Artifact.deleted_at.is_(None),
                        )
                    )
                    result = await db.execute(query)
                    artifact = result.scalar_one_or_none()

                    if not artifact:
                        logger.warning(
                            "Artifact '%s' not found for project %s, skipping",
                            section.title, project_id,
                        )
                        continue

                    # All sections are fully AI-generated
                    contrib = ContributionCategory.UNMODIFIED_AI
                    ai_ratio = 0.0

                    # Use UPDATE statement to ensure the change is persisted
                    new_hash = compute_content_hash(section.content)
                    await db.execute(
                        update(Artifact)
                        .where(Artifact.id == artifact.id)
                        .values(
                            content=section.content,
                            content_hash=new_hash,
                            contribution_category=contrib,
                            ai_modification_ratio=ai_ratio,
                        )
                    )

                    # Create a new version with the generated content
                    version = ArtifactVersion(
                        id=generate_uuid(),
                        artifact_id=artifact.id,
                        version_number=2,  # version 1 was the placeholder
                        title=section.title,
                        content=section.content,
                        content_hash=new_hash,
                        created_by=user_id,
                        contribution_category=contrib,
                    )
                    db.add(version)
                    updated_count += 1

                await db.flush()
                await db.commit()
                logger.info(
                    "Background generation v2 complete for project %s: "
                    "%d sections updated, %d words, %d papers, "
                    "%d verified citations, %d hallucinated",
                    project_id,
                    updated_count,
                    dissertation.total_words,
                    dissertation.total_papers,
                    dissertation.verified_citations,
                    dissertation.hallucinated_citations,
                )
            except Exception as exc:
                logger.error("DB update failed: %s", exc, exc_info=True)
                await db.rollback()
                raise

    except Exception as exc:
        logger.error(
            "Background dissertation generation failed for project %s: %s",
            project_id, exc, exc_info=True,
        )
        import traceback
        print(f"[BACKGROUND] GENERATION FAILED for {project_id}: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    data: ProjectCreate,
    user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Create a new research project.

    1. Creates the project with placeholder scaffold sections instantly
    2. Kicks off background dissertation generation using real academic papers + AI

    Uses pre-generated UUIDs and a single flush to avoid aiosqlite's
    'cannot commit transaction - SQL statements in progress' error.
    """
    from src.kernel.models.base import generate_uuid
    from datetime import datetime, timezone

    project_id = generate_uuid()
    now = datetime.now(timezone.utc)
    discipline_raw = data.discipline_type or "mixed"
    # Ensure discipline is a plain string (not an enum) for the generator
    discipline = discipline_raw.value if hasattr(discipline_raw, 'value') else str(discipline_raw)

    project = ResearchProject(
        id=project_id,
        title=data.title,
        description=data.description,
        discipline_type=discipline,
        owner_id=user.id,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)

    # Auto-scaffold initial dissertation structure (placeholder content)
    scaffold_count = await _scaffold_project_structure(db, project_id, user.id, discipline)

    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_CREATED,
        entity_type="project",
        entity_id=project_id,
        user_id=user.id,
        payload={
            "title": data.title,
            "discipline_type": discipline,
            "scaffolded_sections": scaffold_count,
        },
        ip_address=get_client_ip(request),
    )

    # We MUST commit the scaffold before the background task can see it.
    # Normally get_db() commits after the response, but the background task
    # runs concurrently and needs the data to exist first.
    await db.flush()
    await db.commit()

    # Trigger background dissertation generation using asyncio.create_task()
    # (not BackgroundTasks, which is designed for short post-response cleanup,
    # not 15-minute generation processes)
    asyncio.create_task(
        _background_generate_dissertation(
            project_id=project_id,
            user_id=user.id,
            topic=data.title,
            description=data.description or "",
            discipline=discipline,
        )
    )

    return ProjectResponse(
        id=project_id,
        title=data.title,
        description=data.description,
        discipline_type=discipline,
        status="draft",
        owner_id=user.id,
        owner_name=user.full_name,
        integrity_score=100.0,
        export_blocked=False,
        artifact_count=scaffold_count,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=List[ProjectListResponse])
async def list_projects(
    user: CurrentUser,
    db: DbSession,
    include_shared: bool = Query(True, description="Include projects shared with you"),
    status_filter: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List user's projects (owned and shared)."""
    # Get owned projects
    query = select(ResearchProject, User).join(
        User, ResearchProject.owner_id == User.id
    ).where(
        and_(
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    
    if status_filter:
        query = query.where(ResearchProject.status == status_filter)
    
    result = await db.execute(query)
    owned_projects = result.all()
    
    projects = []
    for project, owner in owned_projects:
        # Count artifacts
        count_query = select(func.count(Artifact.id)).where(
            and_(
                Artifact.project_id == project.id,
                Artifact.deleted_at.is_(None),
            )
        )
        count_result = await db.execute(count_query)
        artifact_count = count_result.scalar() or 0
        
        projects.append(ProjectListResponse(
            id=project.id,
            title=project.title,
            description=project.description,
            discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
            owner_id=project.owner_id,
            owner_name=owner.full_name,
            integrity_score=project.integrity_score,
            is_owner=True,
            permission_level="owner",
            artifact_count=artifact_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        ))
    
    # Get shared projects
    if include_shared:
        shared_query = select(ResearchProject, User, ProjectShare).join(
            ProjectShare, ResearchProject.id == ProjectShare.project_id
        ).join(
            User, ResearchProject.owner_id == User.id
        ).where(
            and_(
                ProjectShare.user_id == user.id,
                ResearchProject.deleted_at.is_(None),
            )
        )
        
        if status_filter:
            shared_query = shared_query.where(ResearchProject.status == status_filter)
        
        shared_result = await db.execute(shared_query)
        
        for project, owner, share in shared_result.all():
            count_query = select(func.count(Artifact.id)).where(
                and_(
                    Artifact.project_id == project.id,
                    Artifact.deleted_at.is_(None),
                )
            )
            count_result = await db.execute(count_query)
            artifact_count = count_result.scalar() or 0
            
            projects.append(ProjectListResponse(
                id=project.id,
                title=project.title,
                description=project.description,
discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
                owner_id=project.owner_id,
                owner_name=owner.full_name,
                integrity_score=project.integrity_score,
                is_owner=False,
                permission_level=_enum_val(share.permission_level),
                artifact_count=artifact_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ))
    
    # Sort by updated_at descending
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    
    return projects[start:end]


@router.get("/{project_id}/document", response_model=ProjectDocumentResponse)
async def get_project_document(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get project artifacts in document order (tree order, depth-first) for read view."""
    query = select(Artifact).where(
        and_(
            Artifact.project_id == project_id,
            Artifact.deleted_at.is_(None),
        )
    ).order_by(Artifact.position)
    result = await db.execute(query)
    artifacts = list(result.scalars().all())
    artifact_map = {a.id: a for a in artifacts}

    def flatten_tree_order(parent_id: Optional[uuid.UUID]) -> List[Artifact]:
        out: List[Artifact] = []
        children = [a for a in artifacts if a.parent_id == parent_id]
        for a in sorted(children, key=lambda x: x.position):
            out.append(a)
            out.extend(flatten_tree_order(a.id))
        return out

    ordered = flatten_tree_order(None)
    chunks = [
        DocumentChunk(
            id=a.id,
            artifact_type=_enum_val(a.artifact_type),
            title=a.title,
            content=a.content or "",
        )
        for a in ordered
    ]
    return ProjectDocumentResponse(project_id=project_id, artifacts=chunks)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Get a project by ID."""
    query = select(ResearchProject, User).join(
        User, ResearchProject.owner_id == User.id
    ).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project, owner = row
    
    # Count artifacts
    count_query = select(func.count(Artifact.id)).where(
        and_(
            Artifact.project_id == project.id,
            Artifact.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_query)
    artifact_count = count_result.scalar() or 0
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
discipline_type=_enum_val(project.discipline_type),
            status=_enum_val(project.status),
        owner_id=project.owner_id,
        owner_name=owner.full_name,
        integrity_score=project.integrity_score,
        export_blocked=project.export_blocked,
        artifact_count=artifact_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("/{project_id}/generate", response_model=SuccessResponse)
async def generate_project_content(
    project_id: uuid.UUID,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Trigger (or re-trigger) AI dissertation generation for a project.

    Searches real academic papers and generates full PhD-level content
    for every section using OpenAI. Runs in the background.
    """
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    discipline = _enum_val(project.discipline_type) or "mixed"

    asyncio.create_task(
        _background_generate_dissertation(
            project_id=project.id,
            user_id=user.id,
            topic=project.title,
            description=project.description or "",
            discipline=discipline,
        )
    )

    return SuccessResponse(
        message="Dissertation generation v2 started. Full PhD content (~50K words) will be generated over the next 15-20 minutes."
    )


@router.get("/{project_id}/generation-status")
async def get_generation_status(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """Check whether AI-generated content has been written into the project.

    Returns per-section word counts so the frontend can show progress.
    """
    query = select(Artifact).where(
        and_(
            Artifact.project_id == project_id,
            Artifact.deleted_at.is_(None),
        )
    ).order_by(Artifact.position)
    result = await db.execute(query)
    artifacts = list(result.scalars().all())

    sections = []
    total_words = 0
    all_generated = True

    for a in artifacts:
        content = a.content or ""
        wc = len(content.split())
        # A section is "generated" if it has more than 200 words
        # (placeholder templates are ~100-200 words)
        is_generated = wc > 200
        if not is_generated:
            all_generated = False
        total_words += wc
        sections.append({
            "title": a.title,
            "word_count": wc,
            "is_generated": is_generated,
        })

    return {
        "project_id": str(project_id),
        "total_words": total_words,
        "total_sections": len(sections),
        "generated_sections": sum(1 for s in sections if s["is_generated"]),
        "all_generated": all_generated,
        "sections": sections,
    }


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    _: RequireProjectEdit,
    user: CurrentUser,
    db: DbSession,
):
    """Update a project."""
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Update fields
    changes = {}
    if data.title is not None:
        changes["previous_title"] = project.title
        project.title = data.title
        changes["new_title"] = data.title
    
    if data.description is not None:
        project.description = data.description
    
    if data.discipline_type is not None:
        changes["previous_discipline"] = _enum_val(project.discipline_type)
        project.discipline_type = data.discipline_type
        changes["new_discipline"] = _enum_val(data.discipline_type)
    
    if data.status is not None:
        changes["previous_status"] = _enum_val(project.status)
        project.status = data.status
        changes["new_status"] = _enum_val(data.status)
    
    # Log the event
    if changes:
        event_store = EventStore(db)
        await event_store.log(
            event_type=EventType.PROJECT_UPDATED,
            entity_type="project",
            entity_id=project.id,
            user_id=user.id,
            payload=changes,
            ip_address=get_client_ip(request),
        )
    
    # Get owner name
    owner_query = select(User).where(User.id == project.owner_id)
    owner_result = await db.execute(owner_query)
    owner = owner_result.scalar_one()
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        discipline_type=_enum_val(project.discipline_type),
        status=_enum_val(project.status),
        owner_id=project.owner_id,
        owner_name=owner.full_name,
        integrity_score=project.integrity_score,
        export_blocked=project.export_blocked,
        artifact_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    request: Request,
    project_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Delete a project (soft delete). Only owner can delete."""
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to delete it",
        )
    
    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_DELETED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={"title": project.title},
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Project deleted successfully")


@router.post("/{project_id}/share", response_model=CollaboratorResponse)
async def share_project(
    request: Request,
    project_id: uuid.UUID,
    data: ProjectShareRequest,
    user: CurrentUser,
    db: DbSession,
):
    """Share a project with another user. Only owner can share."""
    # Verify ownership
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to share it",
        )
    
    # Find user to share with
    target_query = select(User).where(User.email == data.email.lower())
    target_result = await db.execute(target_query)
    target_user = target_result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with that email",
        )
    
    if target_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share project with yourself",
        )
    
    # Check if already shared
    existing_query = select(ProjectShare).where(
        and_(
            ProjectShare.project_id == project_id,
            ProjectShare.user_id == target_user.id,
        )
    )
    existing_result = await db.execute(existing_query)
    existing_share = existing_result.scalar_one_or_none()
    
    if existing_share:
        # Update permission level
        existing_share.permission_level = data.permission_level
    else:
        # Create new share
        share = ProjectShare(
            project_id=project_id,
            user_id=target_user.id,
            permission_level=data.permission_level,
            invited_by=user.id,
        )
        db.add(share)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_SHARED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={
            "shared_with_user_id": str(target_user.id),
            "shared_with_email": target_user.email,
            "permission_level": _enum_val(data.permission_level),
        },
        ip_address=get_client_ip(request),
    )
    
    return CollaboratorResponse(
        user_id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=_enum_val(target_user.role),
        permission_level=_enum_val(data.permission_level),
        is_owner=False,
        accepted=True,
    )


@router.get("/{project_id}/collaborators", response_model=List[CollaboratorResponse])
async def list_collaborators(
    project_id: uuid.UUID,
    _: RequireProjectView,
    user: CurrentUser,
    db: DbSession,
):
    """List all collaborators on a project."""
    permission_service = PermissionService(db)
    return await permission_service.get_project_collaborators(project_id)


@router.delete("/{project_id}/collaborators/{user_id}", response_model=SuccessResponse)
async def remove_collaborator(
    request: Request,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
):
    """Remove a collaborator from a project. Only owner can remove."""
    # Verify ownership
    query = select(ResearchProject).where(
        and_(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == user.id,
            ResearchProject.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission",
        )
    
    # Find and remove share
    share_query = select(ProjectShare).where(
        and_(
            ProjectShare.project_id == project_id,
            ProjectShare.user_id == user_id,
        )
    )
    share_result = await db.execute(share_query)
    share = share_result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found",
        )
    
    await db.delete(share)
    
    # Log the event
    event_store = EventStore(db)
    await event_store.log(
        event_type=EventType.PROJECT_UNSHARED,
        entity_type="project",
        entity_id=project.id,
        user_id=user.id,
        payload={"removed_user_id": str(user_id)},
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Collaborator removed successfully")
