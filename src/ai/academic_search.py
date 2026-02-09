"""
Academic Research Service -- pulls real papers from free scholarly APIs.

Sources:
  - Semantic Scholar (api.semanticscholar.org) -- 200M+ papers, free, no key
  - OpenAlex (api.openalex.org) -- open scholarly metadata, free
  - CrossRef (api.crossref.org) -- DOI metadata, free

All results are normalized into AcademicPaper objects.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AcademicPaper:
    """Normalized paper from any academic API."""
    title: str
    authors: List[str]
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    citation_count: int = 0
    source: str = ""  # "semantic_scholar" | "openalex" | "crossref"
    url: Optional[str] = None
    journal: Optional[str] = None
    fields: List[str] = field(default_factory=list)

    @property
    def short_cite(self) -> str:
        """E.g. 'Smith et al. (2023)'"""
        if not self.authors:
            first = "Unknown"
        else:
            # Safely extract surname from first author
            parts = self.authors[0].split() if self.authors[0] else []
            surname = parts[-1] if parts else "Unknown"
            if len(self.authors) == 1:
                first = surname
            else:
                first = surname + " et al."
        return f"{first} ({self.year or 'n.d.'})"

    @property
    def apa_reference(self) -> str:
        """Rough APA-style reference string."""
        auths = ", ".join(self.authors[:5])
        if len(self.authors) > 5:
            auths += ", ..."
        year_str = str(self.year) if self.year else "n.d."
        title = self.title
        journal_part = f" *{self.journal}*." if self.journal else ""
        doi_part = f" https://doi.org/{self.doi}" if self.doi else ""
        return f"{auths} ({year_str}). {title}.{journal_part}{doi_part}"


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

async def _search_semantic_scholar(
    query: str,
    limit: int = 30,
    *,
    client: httpx.AsyncClient,
) -> List[AcademicPaper]:
    """Search Semantic Scholar Graph API (free, no key)."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,authors,year,abstract,citationCount,externalIds,journal,s2FieldsOfStudy,url",
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)
        return []

    papers: List[AcademicPaper] = []
    for item in data.get("data", []):
        authors = [a.get("name", "") for a in (item.get("authors") or [])]
        doi = (item.get("externalIds") or {}).get("DOI")
        journal_info = item.get("journal") or {}
        journal_name = journal_info.get("name") if isinstance(journal_info, dict) else None
        fields_of_study = [f.get("category", "") for f in (item.get("s2FieldsOfStudy") or [])]
        papers.append(AcademicPaper(
            title=item.get("title", ""),
            authors=authors,
            year=item.get("year"),
            abstract=item.get("abstract"),
            doi=doi,
            citation_count=item.get("citationCount", 0),
            source="semantic_scholar",
            url=item.get("url"),
            journal=journal_name,
            fields=fields_of_study,
        ))
    return papers


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

async def _search_openalex(
    query: str,
    limit: int = 30,
    *,
    client: httpx.AsyncClient,
) -> List[AcademicPaper]:
    """Search OpenAlex API (free, no key, polite pool with mailto)."""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": min(limit, 50),
        "sort": "cited_by_count:desc",
        "mailto": "research-platform@example.com",
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("OpenAlex search failed: %s", exc)
        return []

    papers: List[AcademicPaper] = []
    for item in data.get("results", []):
        authorships = item.get("authorships") or []
        authors = []
        for a in authorships[:10]:
            name = (a.get("author") or {}).get("display_name", "")
            if name:
                authors.append(name)
        doi_url = item.get("doi") or ""
        doi = doi_url.replace("https://doi.org/", "") if doi_url else None
        journal_name = None
        locations = item.get("locations") or item.get("primary_location")
        if isinstance(locations, dict):
            src = locations.get("source") or {}
            journal_name = src.get("display_name")
        elif isinstance(locations, list) and locations:
            src = (locations[0].get("source") or {})
            journal_name = src.get("display_name")

        # Abstract -- OpenAlex returns inverted index, reconstruct
        abstract = None
        inv_index = item.get("abstract_inverted_index")
        if inv_index and isinstance(inv_index, dict):
            try:
                word_positions: list[tuple[str, int]] = []
                for word, positions in inv_index.items():
                    for pos in positions:
                        word_positions.append((word, pos))
                word_positions.sort(key=lambda x: x[1])
                abstract = " ".join(w for w, _ in word_positions)
            except Exception:
                abstract = None

        papers.append(AcademicPaper(
            title=item.get("title") or item.get("display_name", ""),
            authors=authors,
            year=item.get("publication_year"),
            abstract=abstract,
            doi=doi,
            citation_count=item.get("cited_by_count", 0),
            source="openalex",
            url=item.get("id"),
            journal=journal_name,
        ))
    return papers


# ---------------------------------------------------------------------------
# CrossRef
# ---------------------------------------------------------------------------

async def _search_crossref(
    query: str,
    limit: int = 20,
    *,
    client: httpx.AsyncClient,
) -> List[AcademicPaper]:
    """Search CrossRef API (free, no key)."""
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": min(limit, 50),
        "sort": "relevance",
        "order": "desc",
        "select": "DOI,title,author,published-print,is-referenced-by-count,abstract,container-title",
    }
    headers = {"User-Agent": "ResearchPlatform/1.0 (mailto:research-platform@example.com)"}
    try:
        resp = await client.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("CrossRef search failed: %s", exc)
        return []

    papers: List[AcademicPaper] = []
    for item in data.get("message", {}).get("items", []):
        authors = []
        for a in (item.get("author") or [])[:10]:
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{given} {family}".strip())
        title_list = item.get("title") or [""]
        title = title_list[0] if title_list else ""
        pub = item.get("published-print") or item.get("published-online") or {}
        year = None
        date_parts = pub.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
        container = item.get("container-title") or []
        journal_name = container[0] if container else None
        abstract_raw = item.get("abstract", "")
        # CrossRef abstracts often have JATS XML tags
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract_raw).strip() if abstract_raw else None

        papers.append(AcademicPaper(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            doi=item.get("DOI"),
            citation_count=item.get("is-referenced-by-count", 0),
            source="crossref",
            journal=journal_name,
        ))
    return papers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_academic_papers(
    topic: str,
    *,
    max_results: int = 40,
    min_citations: int = 0,
) -> List[AcademicPaper]:
    """
    Search multiple academic APIs in parallel and return deduplicated,
    sorted results.

    Args:
        topic: Research topic / query string
        max_results: Max papers to return after dedup
        min_citations: Filter out papers with fewer citations

    Returns:
        List of AcademicPaper sorted by citation count (descending)
    """
    async with httpx.AsyncClient() as client:
        sem_scholar, openalex, crossref = await asyncio.gather(
            _search_semantic_scholar(topic, limit=40, client=client),
            _search_openalex(topic, limit=40, client=client),
            _search_crossref(topic, limit=30, client=client),
            return_exceptions=True,
        )

    # Collect valid results
    all_papers: List[AcademicPaper] = []
    for batch in (sem_scholar, openalex, crossref):
        if isinstance(batch, list):
            all_papers.extend(batch)
        else:
            logger.warning("Academic search batch failed: %s", batch)

    # Deduplicate by DOI or by (lowered title + year)
    seen: set = set()
    unique: List[AcademicPaper] = []
    for p in all_papers:
        if not p.title:
            continue
        key = p.doi.lower() if p.doi else (p.title.lower().strip()[:120] + str(p.year))
        if key in seen:
            continue
        seen.add(key)
        if p.citation_count >= min_citations:
            unique.append(p)

    # Sort by citations descending
    unique.sort(key=lambda p: p.citation_count, reverse=True)
    return unique[:max_results]
