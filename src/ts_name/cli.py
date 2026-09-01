"""Command-line interface for tailnet name generator."""

import asyncio
import logging
import sys
from collections.abc import Callable

import click
import httpx

from ts_name.filters import FilterOperator
from ts_name.filters import create_filter
from ts_name.generator import TailnetNameGenerator


def _configure_logging(verbose: bool) -> None:
    """Configure application logging after the CLI starts."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("ts_name").setLevel(logging.DEBUG if verbose else logging.INFO)


class SearchProgress:
    _frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self) -> None:
        self.attempts = 0
        self.offers_checked = 0
        self.matches = 0
        self._frame_index = 0
        self._interactive = sys.stderr.isatty()

    def start(self) -> None:
        self._render()

    def update(self, attempts: int, offers_checked: int) -> None:
        self.attempts = attempts
        self.offers_checked = offers_checked
        self._render()

    def match(self) -> None:
        self.matches += 1

    def clear(self) -> None:
        if self._interactive:
            click.echo("\r\033[K", nl=False, err=True)

    def finish(self) -> None:
        self.clear()
        click.echo(
            f"Checked {self.offers_checked} offers in {self.attempts} requests. "
            f"Found {self.matches} matches.",
            err=True,
        )

    def _render(self) -> None:
        if self._interactive:
            frame = self._frames[self._frame_index]
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            click.echo(
                f"\r{frame} Searching... {self.offers_checked} offers checked "
                f"({self.attempts} requests, {self.matches} matches)",
                nl=False,
                err=True,
            )


async def _stream_results(
    generator: TailnetNameGenerator,
    filter_fn: Callable[[str], bool],
    max_iterations: int | None,
    limit: int,
    progress: SearchProgress,
) -> int:
    """Print matching names as the generator finds them."""
    count = 0
    header_shown = False

    async for name, token in generator.generate(
        filter_fn=filter_fn,
        max_iterations=max_iterations,
        progress_fn=progress.update,
    ):
        progress.match()
        progress.clear()
        if not header_shown:
            click.echo("Streaming matching tailnet names:\n")
            header_shown = True

        count += 1
        click.echo(f"{count}. {name} (token: {token})")
        if count >= limit:
            break

    return count


@click.group()
def main() -> None:
    """Tailnet name generator and setter for Tailscale."""
    pass


@main.command()
@click.option(
    "--cookie",
    envvar="TAILSCALE_COOKIE",
    required=True,
    help="Tailscale authentication cookie (or set TAILSCALE_COOKIE env var)",
)
@click.option(
    "--words",
    "-w",
    multiple=True,
    help="Words to filter for (can be used multiple times)",
)
@click.option(
    "--max-length",
    "-m",
    type=click.IntRange(min=1),
    default=None,
    help="Maximum length of tailnet name",
)
@click.option(
    "--min-length",
    type=click.IntRange(min=1),
    default=None,
    help="Minimum length of tailnet name",
)
@click.option(
    "--operator",
    "-o",
    type=click.Choice(["and", "or"], case_sensitive=False),
    default="and",
    help="How to combine word filters (AND or OR)",
)
@click.option(
    "--limit",
    "-l",
    type=click.IntRange(min=1),
    default=10,
    help="Maximum number of results to return",
)
@click.option(
    "--max-iterations",
    type=click.IntRange(min=1),
    default=None,
    help="Maximum number of API calls",
)
@click.option(
    "--delay",
    type=click.FloatRange(min=0),
    default=0.5,
    help="Delay between API requests in seconds",
)
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    default=30.0,
    help="Request timeout in seconds",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def search(
    cookie: str,
    words: tuple[str, ...],
    max_length: int | None,
    min_length: int | None,
    operator: str,
    limit: int,
    max_iterations: int | None,
    delay: float,
    timeout: float,
    verbose: bool,
) -> None:
    """
    Search for matching Tailscale tailnet fun names.

    Examples:

    \b
    # Find names containing "king" and shorter than 10 chars
    ts-name search --cookie YOUR_COOKIE -w king -m 10

    \b
    # Find names containing either "yo" or "ya"
    ts-name search --cookie YOUR_COOKIE -w yo -w ya --operator or

    \b
    # Find short names (max 8 chars)
    ts-name search --cookie YOUR_COOKIE -m 8
    """
    _configure_logging(verbose)

    filter_fn = create_filter(
        words=list(words) or None,
        max_length=max_length,
        min_length=min_length,
        operator=FilterOperator(operator.casefold()),
    )
    generator = TailnetNameGenerator(
        cookie=cookie,
        delay=delay,
        timeout=timeout,
    )
    progress = SearchProgress()
    progress.start()

    try:
        count = asyncio.run(
            _stream_results(generator, filter_fn, max_iterations, limit, progress)
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise click.exceptions.Exit(130) from None
    except httpx.HTTPError as error:
        raise click.ClickException(f"API request failed: {error}") from error
    finally:
        progress.finish()

    if count == 0:
        raise click.ClickException("No matching tailnet names found.")


@main.command()
@click.option(
    "--cookie",
    envvar="TAILSCALE_COOKIE",
    required=True,
    help="Tailscale authentication cookie (or set TAILSCALE_COOKIE env var)",
)
@click.argument("token")
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    default=30.0,
    help="Request timeout in seconds",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def set_name(
    cookie: str,
    token: str,
    timeout: float,
    verbose: bool,
) -> None:
    """
    Set the tailnet name to a specific offer.

    TOKEN: The full token from the search results
           (format: awesome-name.ts.net/timestamp/hash)

    Examples:

    \b
    # Set a specific name using its token
    ts-name set-name --cookie YOUR_COOKIE "awesome-name.ts.net/timestamp/hash"

    \b
    # Using environment variables
    export TAILSCALE_COOKIE="your_cookie"
    ts-name set-name "awesome-name.ts.net/timestamp/hash"
    """
    _configure_logging(verbose)

    parts = token.split("/")
    if len(parts) != 3 or any(not part for part in parts):
        raise click.ClickException(
            "Invalid token format. Expected: tailnet-name.ts.net/timestamp/hash"
        )

    tcd = parts[0]
    generator = TailnetNameGenerator(cookie=cookie, timeout=timeout)

    try:
        asyncio.run(generator.set_name(tcd, token))
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise click.exceptions.Exit(130) from None
    except httpx.HTTPError as error:
        raise click.ClickException(f"Failed to set tailnet name: {error}") from error

    click.echo(f"✓ Successfully set tailnet name to {tcd}")
