"""Unit tests for validation engine."""

import pytest

from src.engines.validation.format_validator import (
    FormatValidator,
    ValidationStatus,
)


class TestFormatValidator:
    """Tests for FormatValidator."""
    
    def test_valid_doi(self):
        """Valid DOI should pass validation."""
        result = FormatValidator.validate_doi("10.1234/example.2024.001")
        assert result.status == ValidationStatus.VALID
    
    def test_doi_with_prefix(self):
        """DOI with URL prefix should be cleaned and validated."""
        result = FormatValidator.validate_doi("https://doi.org/10.1234/example.2024.001")
        assert result.status == ValidationStatus.VALID
        assert result.details["normalized_doi"] == "10.1234/example.2024.001"
    
    def test_invalid_doi(self):
        """Invalid DOI should fail validation."""
        result = FormatValidator.validate_doi("not-a-doi")
        assert result.status == ValidationStatus.INVALID
    
    def test_empty_doi(self):
        """Empty DOI should fail validation."""
        result = FormatValidator.validate_doi("")
        assert result.status == ValidationStatus.INVALID
    
    def test_valid_isbn13(self):
        """Valid ISBN-13 should pass validation."""
        result = FormatValidator.validate_isbn("9780134685991")
        assert result.status == ValidationStatus.VALID
    
    def test_valid_isbn10(self):
        """Valid ISBN-10 should pass validation."""
        result = FormatValidator.validate_isbn("0134685997")
        assert result.status == ValidationStatus.VALID
    
    def test_invalid_isbn_checksum(self):
        """ISBN with invalid checksum should fail."""
        result = FormatValidator.validate_isbn("9780134685999")  # Wrong checksum
        assert result.status == ValidationStatus.INVALID
    
    def test_valid_arxiv_new_format(self):
        """Valid new-format arXiv ID should pass."""
        result = FormatValidator.validate_arxiv("2301.12345")
        assert result.status == ValidationStatus.VALID
    
    def test_valid_arxiv_old_format(self):
        """Valid old-format arXiv ID should pass."""
        result = FormatValidator.validate_arxiv("hep-th/0123456")
        assert result.status == ValidationStatus.VALID
    
    def test_valid_year(self):
        """Valid year should pass validation."""
        result = FormatValidator.validate_year(2024)
        assert result.status == ValidationStatus.VALID
    
    def test_year_too_old(self):
        """Year before printing press should fail."""
        result = FormatValidator.validate_year(1400)
        assert result.status == ValidationStatus.INVALID
    
    def test_year_in_future(self):
        """Future year should give warning."""
        result = FormatValidator.validate_year(2030)
        assert result.status == ValidationStatus.WARNING
    
    def test_required_fields_journal(self):
        """Journal citation should require specific fields."""
        citation_data = {
            "title": "Test Paper",
            "authors": ["Smith, J."],
            "journal": "Test Journal",
            "year": 2024,
        }
        
        results = FormatValidator.validate_required_fields("journal", citation_data)
        assert all(r.status == ValidationStatus.VALID for r in results)
    
    def test_required_fields_missing(self):
        """Missing required fields should be flagged."""
        citation_data = {
            "title": "Test Paper",
            # Missing authors, journal, year
        }
        
        results = FormatValidator.validate_required_fields("journal", citation_data)
        invalid_results = [r for r in results if r.status == ValidationStatus.INVALID]
        assert len(invalid_results) == 3  # authors, journal, year
