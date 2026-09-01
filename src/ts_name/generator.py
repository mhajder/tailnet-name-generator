"""Async tailnet name generator using Tailscale API."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from collections.abc import Callable

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
        self.cookie = cookie
        self.delay = delay
        self.timeout = timeout

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

    async def fetch_offers(self) -> list[dict]:
        """
        Fetch a single batch of tailnet name offers from the API.

        Returns:
            List of tailnet name offers with tcd and token

        Raises:
            httpx.HTTPError: If the API request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.API_URL,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("tcds", [])

    def _is_default_tailscale_name(self, name: str) -> bool:
        """
        Check if a name is a default Tailscale-generated name.

        Default names follow the pattern: tail[hex_digits] (e.g., tail1ab2)
        They are just "tail" followed by hexadecimal characters without hyphens.

        Args:
            name: The tailnet name to check

        Returns:
            True if the name is a default Tailscale name, False otherwise
        """
        if not name.lower().startswith("tail"):
            return False

        # Get the part after "tail"
        remainder = name[4:]

        # Check if remainder is all hexadecimal characters (no hyphens or other chars)
        # Default names are like: tail1ab2, tailabcd, etc.
        return bool(remainder) and all(c in "0123456789abcdefABCDEF" for c in remainder)

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
        iterations = 0

        try:
            while max_iterations is None or iterations < max_iterations:
                try:
                    offers = await self.fetch_offers()
                    iterations += 1

                    for offer in offers:
                        tcd = offer.get("tcd", "")
                        token = offer.get("token", "")
                        if not tcd or not token:
                            continue

                        # Extract just the tailnet name (remove .ts.net suffix)
                        tailnet_name = tcd.replace(".ts.net", "")

                        # Always skip default Tailscale names (tail*)
                        if self._is_default_tailscale_name(tailnet_name):
                            continue

                        if filter_fn is None or filter_fn(tailnet_name):
                            yield (tailnet_name, token)

                    # Rate limiting delay
                    await asyncio.sleep(self.delay)

                except httpx.HTTPError as e:
                    logger.error(f"API request failed: {e}")
                    # Wait before retrying
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
        matches = []
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
            True if successful, False otherwise

        Raises:
            httpx.HTTPError: If the API request fails
        """
        # Ensure tcd has .ts.net suffix
        if not tcd.endswith(".ts.net"):
            tcd = f"{tcd}.ts.net"

        payload = {"tcd": tcd, "token": token}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.SET_URL,
                    headers=self._get_set_headers(),
                    json=payload,
                )
                response.raise_for_status()
                logger.info(f"Successfully set tailnet name to {tcd}")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to set tailnet name: {e}")
            raise
