"""Command-line interface for the tailnet name generator."""

import asyncio
import logging
import sys
from collections.abc import Callable

import click
import httpx

from ts_name.filters import create_filter
from ts_name.generator import TailnetNameGenerator


class DefaultSearchGroup(click.Group):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and args[0] not in {"-h", "--help"}:
            args.insert(0, "search")
        return super().parse_args(ctx, args)


def _configure_logging(verbose: bool) -> None:
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


def _split_any_terms(value: str | None) -> list[str]:
    if value is None:
        return []
    terms = [term.strip() for term in value.split(",") if term.strip()]
    if not terms:
        raise click.BadParameter("must contain at least one term")
    return terms


async def _stream_results(
    generator: TailnetNameGenerator,
    filter_fn: Callable[[str], bool],
    max_requests: int,
    limit: int,
    progress: SearchProgress,
    claim: bool,
) -> int:
    count = 0
    header_shown = False

    async for name, token in generator.generate(
        filter_fn=filter_fn,
        max_iterations=max_requests,
        progress_fn=progress.update,
    ):
        progress.match()
        progress.clear()
        if claim:
            await generator.set_name(name, token)
            click.echo(f"✓ Successfully claimed tailnet name: {name}")
            return 1
        if not header_shown:
            click.echo("Streaming matching tailnet names:\n")
            header_shown = True

        count += 1
        click.echo(f"{count}. {name} (token: {token})")
        if count >= limit:
            break

    return count


@click.group(cls=DefaultSearchGroup)
def main() -> None:
    """Search for or claim Tailscale tailnet names."""


@main.command(help="Search generated tailnet names.")
@click.argument("terms", nargs=-1)
@click.option(
    "--any",
    "any_terms",
    help="Comma-separated alternatives. One must match.",
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
    "--limit",
    "-l",
    type=click.IntRange(min=1),
    default=1,
    help="Maximum number of results to return",
)
@click.option(
    "--max-requests",
    type=click.IntRange(min=1),
    default=1000,
    show_default=True,
    help="Maximum number of API requests",
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
    "--cookie",
    envvar="TAILSCALE_COOKIE",
    required=True,
    help="Tailscale authentication cookie",
)
@click.option(
    "--claim",
    is_flag=True,
    help="Claim the first matching name and stop",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def search(
    terms: tuple[str, ...],
    any_terms: str | None,
    max_length: int | None,
    min_length: int | None,
    limit: int,
    max_requests: int,
    delay: float,
    timeout: float,
    cookie: str,
    claim: bool,
    verbose: bool,
) -> None:
    _configure_logging(verbose)
    alternatives = _split_any_terms(any_terms)
    if not terms and not alternatives and max_length is None and min_length is None:
        raise click.UsageError("provide search terms or use --any")

    filter_fn = create_filter(
        all_terms=list(terms),
        any_terms=alternatives,
        max_length=max_length,
        min_length=min_length,
    )
    generator = TailnetNameGenerator(cookie, delay=delay, timeout=timeout)
    progress = SearchProgress()
    progress.start()

    try:
        count = asyncio.run(
            _stream_results(
                generator,
                filter_fn,
                max_requests,
                limit,
                progress,
                claim,
            )
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise click.exceptions.Exit(130) from None
    except httpx.HTTPError as error:
        raise click.ClickException(f"API request failed: {error}") from error
    finally:
        progress.finish()

    if count == 0:
        raise click.ClickException("No matching tailnet names found.")


@main.command(help="Claim a tailnet name from an offer token.")
@click.argument("token")
@click.option(
    "--timeout",
    type=click.FloatRange(min=0, min_open=True),
    default=30.0,
    help="Request timeout in seconds",
)
@click.option(
    "--cookie",
    envvar="TAILSCALE_COOKIE",
    required=True,
    help="Tailscale authentication cookie",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def claim(token: str, timeout: float, cookie: str, verbose: bool) -> None:
    _configure_logging(verbose)
    parts = token.split("/")
    if len(parts) != 3 or any(not part for part in parts):
        raise click.ClickException(
            "Invalid token format. Expected: tailnet-name.ts.net/timestamp/hash"
        )

    tcd = parts[0]
    generator = TailnetNameGenerator(cookie, timeout=timeout)
    try:
        asyncio.run(generator.set_name(tcd, token))
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise click.exceptions.Exit(130) from None
    except httpx.HTTPError as error:
        raise click.ClickException(f"Failed to claim tailnet name: {error}") from error

    click.echo(f"✓ Successfully claimed tailnet name: {tcd.removesuffix('.ts.net')}")
