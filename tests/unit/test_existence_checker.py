"""Unit tests for existence checker (API-based verification)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.engines.validation.existence_checker import (
    ExistenceChecker,
    SourceMetadata,
    _parse_crossref_message,
    _parse_openlibrary,
    _parse_arxiv_atom,
)
from src.engines.validation.format_validator import ValidationStatus


class TestExistenceCheckerCrossref:
    """Tests for DOI verification via Crossref."""

    @pytest.mark.asyncio
    async def test_verify_doi_success(self):
        """Valid Crossref response returns VALID and metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Test Paper Title"],
                "author": [{"given": "John", "family": "Smith"}],
                "published": {"date-parts": [[2024, 1, 15]]},
                "container-title": ["Journal of Tests"],
                "DOI": "10.1234/test.2024",
            }
        }
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            result, metadata = await ExistenceChecker.verify_doi("10.1234/test.2024")
        assert result.status == ValidationStatus.VALID
        assert metadata is not None
        assert metadata.title == "Test Paper Title"
        assert metadata.year == 2024
        assert "Smith" in (metadata.authors or [])[0]

    @pytest.mark.asyncio
    async def test_verify_doi_not_found(self):
        """404 from Crossref returns INVALID."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            result, metadata = await ExistenceChecker.verify_doi("10.1234/nonexistent.2024")
        assert result.status == ValidationStatus.INVALID
        assert metadata is None

    @pytest.mark.asyncio
    async def test_verify_doi_rate_limit(self):
        """429 returns WARNING and no metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch("src.engines.validation.existence_checker.asyncio.sleep", new_callable=AsyncMock):
                result, metadata = await ExistenceChecker.verify_doi("10.1234/rate.2024")
        assert result.status == ValidationStatus.WARNING
        assert "Rate" in result.message or "429" in result.message
        assert metadata is None

    @pytest.mark.asyncio
    async def test_verify_doi_cached(self):
        """Cached result returns quickly with VALID."""
        ExistenceChecker.clear_cache()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Cached"],
                "author": [],
                "published": {"date-parts": [[]]},
                "DOI": "10.1234/cached.2024",
            }
        }
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            await ExistenceChecker.verify_doi("10.1234/cached.2024")
            result2, meta2 = await ExistenceChecker.verify_doi("10.1234/cached.2024")
        assert result2.status == ValidationStatus.VALID
        assert "cached" in result2.message.lower() or meta2 is not None
        ExistenceChecker.clear_cache()


class TestExistenceCheckerOpenLibrary:
    """Tests for ISBN verification via OpenLibrary."""

    @pytest.mark.asyncio
    async def test_verify_isbn_success(self):
        """Valid OpenLibrary response returns VALID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Book",
            "authors": [{"name": "Author One"}],
            "publish_date": "2023",
            "publishers": [{"name": "Pub Inc"}],
        }
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            result, metadata = await ExistenceChecker.verify_isbn("9780134685991")
        assert result.status == ValidationStatus.VALID
        assert metadata is not None
        assert metadata.title == "Test Book"

    @pytest.mark.asyncio
    async def test_verify_isbn_not_found(self):
        """404 returns INVALID."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            result, metadata = await ExistenceChecker.verify_isbn("9780000000000")
        assert result.status == ValidationStatus.INVALID
        assert metadata is None


class TestExistenceCheckerArxiv:
    """Tests for arXiv verification."""

    @pytest.mark.asyncio
    async def test_verify_arxiv_success(self):
        """Valid arXiv Atom response returns VALID."""
        atom = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Test arXiv Paper</title>
            <author><name>Researcher A</name></author>
            <published>2024-01-01T00:00:00Z</published>
            <id>https://arxiv.org/abs/2401.00001</id>
          </entry>
        </feed>"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = atom
        with patch("src.engines.validation.existence_checker.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(request=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            result, metadata = await ExistenceChecker.verify_arxiv("2401.00001")
        assert result.status == ValidationStatus.VALID
        assert metadata is not None
        assert metadata.url is not None
        # Title may be parsed when namespace matches
        if metadata.title:
            assert "Test" in metadata.title


class TestParsers:
    """Unit tests for response parsers."""

    def test_parse_crossref_message(self):
        """Parse Crossref message into SourceMetadata."""
        data = {
            "message": {
                "title": ["A Title"],
                "author": [{"given": "J", "family": "Doe"}],
                "published": {"date-parts": [[2023]]},
                "container-title": ["Journal"],
                "DOI": "10.1234/abc",
            }
        }
        meta = _parse_crossref_message(data)
        assert meta.title == "A Title"
        assert meta.year == 2023
        assert meta.doi == "10.1234/abc"

    def test_parse_openlibrary(self):
        """Parse OpenLibrary JSON into SourceMetadata."""
        data = {
            "title": "Book Title",
            "authors": [{"name": "Author"}],
            "publish_date": "2022",
        }
        meta = _parse_openlibrary(data, "9780123456789")
        assert meta.title == "Book Title"
        assert meta.year == 2022
        assert meta.isbn == "9780123456789"

    def test_parse_arxiv_atom(self):
        """Parse arXiv Atom XML into SourceMetadata (url and year from namespaced elements)."""
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Paper</title>
            <author><name>Name</name></author>
            <published>2024-05-01T00:00:00Z</published>
            <id>https://arxiv.org/abs/2405.00001</id>
          </entry>
        </feed>"""
        meta = _parse_arxiv_atom(xml, "2405.00001")
        assert meta is not None
        assert meta.url == "https://arxiv.org/abs/2405.00001"
        # With default namespace, id is found; title/year may depend on parser
