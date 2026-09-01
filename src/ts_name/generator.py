"""Async tailnet name generator using Tailscale API."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from collections.abc import Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TailnetNameGenerator:
    """Async generator for Tailscale tailnet fun names."""

    API_URL = "https://login.tailscale.com/admin/api/public/admin/tcd/offers"
    SET_URL = "https://login.tailscale.com/admin/api/public/admin/tcd"
    DEFAULT_DELAY = 0.5  # seconds, to avoid rate limiting

    def __init__(
        self,
        cookie: str,
        delay: float = DEFAULT_DELAY,
        timeout: float = 30.0,
    ):
        """
        Initialize the generator.

        Args:
            cookie: Tailscale authentication cookie
            delay: Delay between requests in seconds (default: 0.5)
            timeout: Request timeout in seconds (default: 30.0)
        """
        if delay < 0:
            raise ValueError("delay cannot be negative")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.cookie = cookie
        self.delay = delay
        self.timeout = timeout

    def _create_client(self) -> httpx.AsyncClient:
        """Create an HTTP client for Tailscale requests."""
        return httpx.AsyncClient(timeout=self.timeout)

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "cookie": self.cookie,
            "Referer": "https://login.tailscale.com/admin/dns",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def _get_set_headers(self) -> dict[str, str]:
        """Build request headers for setting a tailnet name."""
        headers = self._get_headers()
        headers["content-type"] = "application/json"
        headers["priority"] = "u=1, i"
        return headers

    async def fetch_offers(self) -> list[dict[str, Any]]:
        """
        Fetch a single batch of tailnet name offers from the API.

        Returns:
            List of tailnet name offers with tcd and token

        Raises:
            httpx.HTTPError: If the API request fails
        """
        async with self._create_client() as client:
            return await self._fetch_offers(client)

    async def _fetch_offers(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch offers using an existing HTTP client."""
        response = await client.get(
            self.API_URL,
            headers=self._get_headers(),
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return []

        response_data = data.get("data")
        if not isinstance(response_data, dict):
            return []

        offers = response_data.get("tcds")
        if not isinstance(offers, list):
            return []
        return [offer for offer in offers if isinstance(offer, dict)]

    @staticmethod
    def _is_default_tailscale_name(name: str) -> bool:
        """
        Check if a name is a default Tailscale-generated name.

        Default names follow the pattern: tail[hex_digits] (e.g., tail1ab2)
        They are just "tail" followed by hexadecimal characters without hyphens.

        Args:
            name: The tailnet name to check

        Returns:
            True if the name is a default Tailscale name, False otherwise
        """
        name = name.casefold()
        remainder = name[4:]
        return (
            name.startswith("tail")
            and bool(remainder)
            and all(character in "0123456789abcdef" for character in remainder)
        )

    async def generate(
        self,
        filter_fn: Callable[[str], bool] | None = None,
        max_iterations: int | None = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Generate matching tailnet names asynchronously.

        Args:
            filter_fn: Optional filter function that takes a tailnet name
                      and returns True if it matches criteria
            max_iterations: Maximum number of API calls (None for infinite)

        Yields:
            Tuples of (tailnet_name, token) for matching names
        """
        attempts = 0

        try:
            async with self._create_client() as client:
                while max_iterations is None or attempts < max_iterations:
                    attempts += 1
                    try:
                        offers = await self._fetch_offers(client)
                    except httpx.HTTPError as error:
                        logger.warning("API request failed: %s", error)
                        if max_iterations is not None and attempts >= max_iterations:
                            raise
                        await asyncio.sleep(self.delay)
                        continue

                    for offer in offers:
                        tcd = offer.get("tcd")
                        token = offer.get("token")
                        if not isinstance(tcd, str) or not isinstance(token, str):
                            continue

                        tailnet_name = tcd.removesuffix(".ts.net")
                        if not tailnet_name or self._is_default_tailscale_name(
                            tailnet_name
                        ):
                            continue

                        if filter_fn is None or filter_fn(tailnet_name):
                            yield tailnet_name, token

                    if max_iterations is None or attempts < max_iterations:
                        await asyncio.sleep(self.delay)

        except asyncio.CancelledError:
            logger.info("Generator cancelled")
            raise

    async def generate_with_limit(
        self,
        filter_fn: Callable[[str], bool] | None = None,
        max_matches: int = 10,
        max_iterations: int | None = None,
    ) -> list[tuple[str, str]]:
        """
        Generate tailnet names until a limit is reached.

        Args:
            filter_fn: Optional filter function
            max_matches: Maximum number of matching names to return
            max_iterations: Maximum number of API calls

        Returns:
            List of tuples containing (tailnet_name, token)
        """
        if max_matches < 1:
            raise ValueError("max_matches must be positive")

        matches: list[tuple[str, str]] = []
        async for name, token in self.generate(filter_fn, max_iterations):
            matches.append((name, token))
            if len(matches) >= max_matches:
                break
        return matches

    async def set_name(self, tcd: str, token: str) -> bool:
        """
        Set the tailnet name to a specific offer.

        Args:
            tcd: The tailnet name (e.g., "awesome-name.ts.net")
            token: The token from the offer

        Returns:
            True if the request succeeds

        Raises:
            httpx.HTTPError: If the API request fails
        """
        tcd = tcd if tcd.endswith(".ts.net") else f"{tcd}.ts.net"
        payload = {"tcd": tcd, "token": token}

        async with self._create_client() as client:
            response = await client.post(
                self.SET_URL,
                headers=self._get_set_headers(),
                json=payload,
            )
            response.raise_for_status()

        logger.info("Successfully set tailnet name to %s", tcd)
        return True
