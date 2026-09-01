"""Tests for filter logic."""

import pytest

from ts_name.filters import FilterConfig
from ts_name.filters import create_filter


class TestFilterConfig:
    """Tests for FilterConfig dataclass."""

    def test_basic_and_filter(self) -> None:
        """Test matching all required terms."""
        config = FilterConfig(all_terms=["king", "ratio"])
        assert config.matches("king-ratio")
        assert not config.matches("king-hen")
        assert not config.matches("great-ratio")

    def test_basic_or_filter(self) -> None:
        """Test matching one alternative term."""
        config = FilterConfig(all_terms=[], any_terms=["king", "ratio"])
        assert config.matches("king-ratio")
        assert config.matches("king-hen")
        assert config.matches("great-ratio")
        assert not config.matches("great-hen")

    def test_max_length_filter(self) -> None:
        """Test maximum length filtering."""
        config = FilterConfig(all_terms=[], max_length=10)
        assert config.matches("short")
        assert config.matches("tencharnam")
        assert not config.matches("toolongname")

    def test_min_length_filter(self) -> None:
        """Test minimum length filtering."""
        config = FilterConfig(all_terms=[], min_length=5)
        assert not config.matches("tiny")
        assert config.matches("quite")
        assert config.matches("longername")

    def test_combined_length_filter(self) -> None:
        """Test both min and max length together."""
        config = FilterConfig(
            all_terms=[],
            min_length=3,
            max_length=8,
        )
        assert not config.matches("ab")
        assert config.matches("abc")
        assert config.matches("abcdefgh")
        assert not config.matches("abcdefghi")

    def test_invalid_length_range(self) -> None:
        """Test that invalid length range raises error."""
        with pytest.raises(ValueError, match="min_length"):
            FilterConfig(all_terms=[], min_length=10, max_length=5)

    def test_case_insensitive_matching(self) -> None:
        """Test that term matching is case-insensitive."""
        config = FilterConfig(all_terms=["King"])
        assert config.matches("king-ratio")
        assert config.matches("KING-RATIO")
        assert config.matches("King-Ratio")

    def test_empty_terms_list(self) -> None:
        """Test that empty terms match everything."""
        config = FilterConfig(all_terms=[])
        assert config.matches("anything")
        assert config.matches("xyz")

    def test_partial_term_match(self) -> None:
        """Test that partial term matches work."""
        config = FilterConfig(all_terms=[], any_terms=["yo"])
        assert config.matches("yogi-bear")
        assert config.matches("king-yo")
        assert config.matches("yo-yo")


class TestCreateFilter:
    """Tests for create_filter helper function."""

    def test_create_filter_all_terms(self) -> None:
        """Test creating a filter for required terms."""
        filter_fn = create_filter(all_terms=["king", "ratio"])
        assert filter_fn("king-ratio")
        assert not filter_fn("king-hen")

    def test_create_filter_any_terms(self) -> None:
        """Test creating a filter for alternative terms."""
        filter_fn = create_filter(any_terms=["king", "ratio"])
        assert filter_fn("king-ratio")
        assert filter_fn("king-hen")
        assert filter_fn("great-ratio")
        assert not filter_fn("great-hen")

    def test_create_filter_with_length(self) -> None:
        """Test creating a filter with length constraints."""
        filter_fn = create_filter(max_length=8)
        assert filter_fn("short")
        assert not filter_fn("verylongname")

    def test_create_filter_no_terms(self) -> None:
        """Test creating a filter without terms."""
        filter_fn = create_filter()
        assert filter_fn("anything")

    def test_create_filter_all_options(self) -> None:
        """Test creating a filter with all options."""
        filter_fn = create_filter(
            all_terms=["king"],
            min_length=4,
            max_length=12,
        )
        assert filter_fn("king-n")
        assert not filter_fn("kin")
        assert not filter_fn("king-verylongname")
        assert not filter_fn("great-ratio")
