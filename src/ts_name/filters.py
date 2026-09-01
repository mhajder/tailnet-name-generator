"""Filter logic for tailnet names with AND/OR support."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class FilterOperator(Enum):
    """Filter operator for combining multiple filters."""

    AND = "and"
    OR = "or"


@dataclass
class FilterConfig:
    """Configuration for filtering tailnet names."""

    words: list[str]
    max_length: int | None = None
    min_length: int | None = None
    operator: FilterOperator = FilterOperator.AND

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("min_length cannot be negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length cannot be negative")
        if (
            self.max_length is not None
            and self.min_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError(
                f"min_length ({self.min_length}) cannot be greater than "
                f"max_length ({self.max_length})"
            )

    def matches(self, tailnet_name: str) -> bool:
        """
        Check if a tailnet name matches the filter criteria.

        Args:
            tailnet_name: The tailnet name to check (e.g., "awesome-name")

        Returns:
            True if the name matches all criteria, False otherwise
        """
        name = tailnet_name.casefold()
        if self.max_length is not None and len(tailnet_name) > self.max_length:
            return False
        if self.min_length is not None and len(tailnet_name) < self.min_length:
            return False
        if not self.words:
            return True

        matches = (word.casefold() in name for word in self.words)
        return all(matches) if self.operator == FilterOperator.AND else any(matches)


def create_filter(
    words: list[str] | None = None,
    max_length: int | None = None,
    min_length: int | None = None,
    operator: FilterOperator = FilterOperator.AND,
) -> Callable[[str], bool]:
    """
    Create a filter function for tailnet names.

    Args:
        words: List of words to filter by
        max_length: Maximum length of tailnet name
        min_length: Minimum length of tailnet name
        operator: How to combine word filters (AND or OR)

    Returns:
        A filter function that takes a tailnet name and returns True if it matches
    """
    config = FilterConfig(
        words=words or [],
        max_length=max_length,
        min_length=min_length,
        operator=operator,
    )
    return config.matches
