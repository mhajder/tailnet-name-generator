"""Filter logic for tailnet names."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class FilterConfig:
    """Configuration for filtering tailnet names."""

    all_terms: list[str]
    any_terms: list[str] | None = None
    max_length: int | None = None
    min_length: int | None = None

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
        """Check whether a tailnet name matches the filter criteria."""
        if self.max_length is not None and len(tailnet_name) > self.max_length:
            return False
        if self.min_length is not None and len(tailnet_name) < self.min_length:
            return False

        name = tailnet_name.casefold()
        if not all(term.casefold() in name for term in self.all_terms):
            return False
        return not self.any_terms or any(
            term.casefold() in name for term in self.any_terms
        )


def create_filter(
    all_terms: list[str] | None = None,
    any_terms: list[str] | None = None,
    max_length: int | None = None,
    min_length: int | None = None,
) -> Callable[[str], bool]:
    """Create a filter function for tailnet names."""
    config = FilterConfig(
        all_terms=all_terms or [],
        any_terms=any_terms,
        max_length=max_length,
        min_length=min_length,
    )
    return config.matches
