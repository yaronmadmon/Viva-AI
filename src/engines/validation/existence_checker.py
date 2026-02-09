"""
Layer 2: Existence Check - API-based verification.

Verifies that sources actually exist using external APIs:
- Crossref for DOIs
- OpenLibrary for ISBNs
- arXiv API for arXiv IDs

Results are cached for 24 hours. Retry with exponential backoff for 5xx/timeouts.
Rate limit (429) returns WARNING and is not cached as success.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel

from src.engines.validation.format_validator import ValidationResult, ValidationStatus
from src.logging_config import get_logger

logger = get_logger(__name__)

# Default timeout and retry
HTTP_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_BACKOFF = (1.0, 2.0, 4.0)  # seconds


class SourceMetadata(BaseModel):
    """Metadata retrieved from external API."""

    title: Optional[str] = None
    authors: Optional[list] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


def _parse_crossref_message(data: dict) -> SourceMetadata:
    """Parse Crossref API response message into SourceMetadata."""
    message = data.get("message", {})
    title_list = message.get("title", [])
    title = title_list[0] if title_list else None
    author_list = message.get("author", [])
    authors = []
    for a in author_list:
        given = a.get("given", "")
        family = a.get("family", "")
        if family:
            authors.append(f"{family}, {given}".strip(", ") if given else family)
    published = message.get("published", {}).get("date-parts", [[]])
    year = int(published[0][0]) if published and published[0] else None
    container = message.get("container-title", [])
    journal = container[0] if container else None
    doi = message.get("DOI")
    return SourceMetadata(
        title=title,
        authors=authors or None,
        year=year,
        journal=journal,
        doi=doi,
    )


def _parse_openlibrary(data: dict, isbn: str) -> SourceMetadata:
    """Parse OpenLibrary ISBN response into SourceMetadata."""
    title = data.get("title")
    publishers = data.get("publishers", [])
    publisher = publishers[0].get("name") if publishers else None
    # authors can be list of dicts with "name" or keys
    author_list = data.get("authors", []) or data.get("contributors", [])
    authors = []
    for a in author_list:
        if isinstance(a, dict):
            name = a.get("name")
            if name:
                authors.append(name)
        else:
            authors.append(str(a))
    pub_date = data.get("publish_date") or data.get("publish_date")
    year = None
    if isinstance(pub_date, str) and len(pub_date) >= 4:
        try:
            year = int(pub_date[:4])
        except ValueError:
            pass
    return SourceMetadata(
        title=title,
        authors=authors or None,
        year=year,
        publisher=publisher,
        isbn=isbn,
    )


ATOM_NS = "http://www.w3.org/2005/Atom"


def _parse_arxiv_atom(xml_text: str, arxiv_id: str) -> Optional[SourceMetadata]:
    """Parse arXiv Atom XML feed into SourceMetadata."""
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": ATOM_NS}
        # Support both namespaced and non-namespaced tags
        entry = root.find(f"{{{ATOM_NS}}}entry") or root.find("atom:entry", ns) or root.find("entry")
        if entry is None:
            entries = root.findall(f".//{{{ATOM_NS}}}entry") or root.findall(".//atom:entry", ns) or root.findall(".//entry")
            entry = entries[0] if entries else None
        if entry is None:
            return None
        title_el = entry.find(f"{{{ATOM_NS}}}title") or entry.find("atom:title", ns) or entry.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else None
        authors = []
        for author in entry.findall(f"{{{ATOM_NS}}}author") or entry.findall("atom:author", ns) or entry.findall("author"):
            name_el = author.find(f"{{{ATOM_NS}}}name") or author.find("atom:name", ns) or author.find("name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        published_el = entry.find(f"{{{ATOM_NS}}}published") or entry.find("atom:published", ns) or entry.find("published")
        year = None
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except (ValueError, TypeError):
                pass
        id_el = entry.find(f"{{{ATOM_NS}}}id") or entry.find("atom:id", ns) or entry.find("id")
        url = id_el.text if id_el is not None and id_el.text else f"https://arxiv.org/abs/{arxiv_id}"
        return SourceMetadata(
            title=title,
            authors=authors or None,
            year=year,
            url=url,
        )
    except ET.ParseError as e:
        logger.warning("arXiv XML parse error: %s", e)
        return None


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Perform request with exponential backoff for 5xx and timeouts. On 429, retry once after delay."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
                    continue
                return response
            if response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
                continue
            return response
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])
    if last_exc:
        raise last_exc
    return await client.request(method, url, **kwargs)


class ExistenceChecker:
    """
    Layer 2: Verify source existence via external APIs.
    Uses Crossref, OpenLibrary, and arXiv with retry and rate-limit handling.
    """

    CACHE_TTL = timedelta(hours=24)
    _cache: Dict[str, tuple[datetime, SourceMetadata]] = {}

    @classmethod
    async def verify_doi(cls, doi: str) -> tuple[ValidationResult, Optional[SourceMetadata]]:
        """Verify DOI exists via Crossref API."""
        cache_key = f"doi:{doi}"
        if cache_key in cls._cache:
            cached_time, metadata = cls._cache[cache_key]
            if datetime.now() - cached_time < cls.CACHE_TTL:
                return (
                    ValidationResult(
                        status=ValidationStatus.VALID,
                        layer=2,
                        message="DOI verified (cached)",
                        field="doi",
                        details={"source": "cache"},
                    ),
                    metadata,
                )

        url = f"https://api.crossref.org/works/{doi}"
        try:
            async with httpx.AsyncClient() as client:
                response = await _request_with_retry(client, "GET", url, timeout=HTTP_TIMEOUT)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("Crossref request failed for DOI %s: %s", doi, e)
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Could not verify DOI (network error)",
                    field="doi",
                    details={"error": str(e)},
                ),
                None,
            )

        if response.status_code == 429:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Rate limited by Crossref; try again later",
                    field="doi",
                    details={"api": "crossref"},
                ),
                None,
            )
        if response.status_code == 404:
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=2,
                    message="DOI not found",
                    field="doi",
                    details={"api": "crossref"},
                ),
                None,
            )
        if response.status_code != 200:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message=f"Crossref returned {response.status_code}",
                    field="doi",
                    details={"api": "crossref", "status": response.status_code},
                ),
                None,
            )

        try:
            data = response.json()
            metadata = _parse_crossref_message(data)
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Crossref parse error for DOI %s: %s", doi, e)
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Invalid response from Crossref",
                    field="doi",
                    details={"error": str(e)},
                ),
                None,
            )

        cls._cache[cache_key] = (datetime.now(), metadata)
        return (
            ValidationResult(
                status=ValidationStatus.VALID,
                layer=2,
                message="DOI verified",
                field="doi",
                details={"api": "crossref"},
            ),
            metadata,
        )

    @classmethod
    async def verify_isbn(cls, isbn: str) -> tuple[ValidationResult, Optional[SourceMetadata]]:
        """Verify ISBN exists via OpenLibrary API."""
        cache_key = f"isbn:{isbn}"
        if cache_key in cls._cache:
            cached_time, metadata = cls._cache[cache_key]
            if datetime.now() - cached_time < cls.CACHE_TTL:
                return (
                    ValidationResult(
                        status=ValidationStatus.VALID,
                        layer=2,
                        message="ISBN verified (cached)",
                        field="isbn",
                        details={"source": "cache"},
                    ),
                    metadata,
                )

        url = f"https://openlibrary.org/isbn/{isbn}.json"
        try:
            async with httpx.AsyncClient() as client:
                response = await _request_with_retry(client, "GET", url, timeout=HTTP_TIMEOUT)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("OpenLibrary request failed for ISBN %s: %s", isbn, e)
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Could not verify ISBN (network error)",
                    field="isbn",
                    details={"error": str(e)},
                ),
                None,
            )

        if response.status_code == 429:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Rate limited by OpenLibrary; try again later",
                    field="isbn",
                    details={"api": "openlibrary"},
                ),
                None,
            )
        if response.status_code == 404:
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=2,
                    message="ISBN not found",
                    field="isbn",
                    details={"api": "openlibrary"},
                ),
                None,
            )
        if response.status_code != 200:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message=f"OpenLibrary returned {response.status_code}",
                    field="isbn",
                    details={"api": "openlibrary", "status": response.status_code},
                ),
                None,
            )

        try:
            data = response.json()
            metadata = _parse_openlibrary(data, isbn)
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("OpenLibrary parse error for ISBN %s: %s", isbn, e)
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Invalid response from OpenLibrary",
                    field="isbn",
                    details={"error": str(e)},
                ),
                None,
            )

        cls._cache[cache_key] = (datetime.now(), metadata)
        return (
            ValidationResult(
                status=ValidationStatus.VALID,
                layer=2,
                message="ISBN verified",
                field="isbn",
                details={"api": "openlibrary"},
            ),
            metadata,
        )

    @classmethod
    async def verify_arxiv(cls, arxiv_id: str) -> tuple[ValidationResult, Optional[SourceMetadata]]:
        """Verify arXiv ID exists via arXiv API."""
        cache_key = f"arxiv:{arxiv_id}"
        if cache_key in cls._cache:
            cached_time, metadata = cls._cache[cache_key]
            if datetime.now() - cached_time < cls.CACHE_TTL:
                return (
                    ValidationResult(
                        status=ValidationStatus.VALID,
                        layer=2,
                        message="arXiv ID verified (cached)",
                        field="arxiv",
                        details={"source": "cache"},
                    ),
                    metadata,
                )

        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        try:
            async with httpx.AsyncClient() as client:
                response = await _request_with_retry(client, "GET", url, timeout=HTTP_TIMEOUT)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("arXiv request failed for %s: %s", arxiv_id, e)
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Could not verify arXiv ID (network error)",
                    field="arxiv",
                    details={"error": str(e)},
                ),
                None,
            )

        if response.status_code == 429:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message="Rate limited by arXiv; try again later",
                    field="arxiv",
                    details={"api": "arxiv"},
                ),
                None,
            )
        if response.status_code != 200:
            return (
                ValidationResult(
                    status=ValidationStatus.WARNING,
                    layer=2,
                    message=f"arXiv returned {response.status_code}",
                    field="arxiv",
                    details={"api": "arxiv", "status": response.status_code},
                ),
                None,
            )

        metadata = _parse_arxiv_atom(response.text, arxiv_id)
        if metadata is None:
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    layer=2,
                    message="arXiv ID not found or invalid response",
                    field="arxiv",
                    details={"api": "arxiv"},
                ),
                None,
            )

        if not metadata.url:
            metadata.url = f"https://arxiv.org/abs/{arxiv_id}"
        cls._cache[cache_key] = (datetime.now(), metadata)
        return (
            ValidationResult(
                status=ValidationStatus.VALID,
                layer=2,
                message="arXiv ID verified",
                field="arxiv",
                details={"api": "arxiv"},
            ),
            metadata,
        )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the verification cache."""
        cls._cache.clear()
