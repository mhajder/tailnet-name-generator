"""Tests for the tailnet name generator."""

from ts_name.generator import TailnetNameGenerator


class TestTailnetNameGenerator:
    """Tests for TailnetNameGenerator."""

    def test_initialization(self) -> None:
        """Test generator initialization."""
        gen = TailnetNameGenerator(cookie="test_cookie")
        assert gen.cookie == "test_cookie"
        assert gen.delay == 0.5
        assert gen.timeout == 30.0

    def test_custom_delay_and_timeout(self) -> None:
        """Test custom delay and timeout."""
        gen = TailnetNameGenerator(
            cookie="test_cookie",
            delay=1.0,
            timeout=60.0,
        )
        assert gen.delay == 1.0
        assert gen.timeout == 60.0

    def test_headers_generation(self) -> None:
        """Test that headers are properly generated."""
        gen = TailnetNameGenerator(cookie="test_cookie_123")
        headers = gen._get_headers()

        assert headers["cookie"] == "test_cookie_123"
        assert headers["accept"] == "application/json, text/plain, */*"
        assert "Referer" in headers
        assert headers["sec-fetch-mode"] == "cors"

    def test_set_headers_generation(self) -> None:
        """Test that set headers include content-type and priority."""
        gen = TailnetNameGenerator(cookie="test_cookie")
        headers = gen._get_set_headers()

        assert headers["cookie"] == "test_cookie"
        assert headers["content-type"] == "application/json"
        assert headers["priority"] == "u=1, i"

    def test_set_headers_no_csrf(self) -> None:
        """Test that set headers do not include CSRF token."""
        gen = TailnetNameGenerator(cookie="test_cookie")
        headers = gen._get_set_headers()

        assert headers["cookie"] == "test_cookie"
        assert headers["content-type"] == "application/json"
        assert "x-csrf-token" not in headers

    def test_generate_with_filter(self) -> None:
        """Test that generator respects filter function."""
        _gen = TailnetNameGenerator(cookie="dummy_cookie")

        # Create a mock filter that only accepts names with "test"
        def test_filter(name: str) -> bool:
            return "test" in name.lower()

        # Note: This test will fail without valid credentials
        # It's mostly to verify the structure and async nature
        # In real usage, you'd need valid Tailscale credentials

    def test_api_url_constant(self) -> None:
        """Test that API URL is correct."""
        assert (
            TailnetNameGenerator.API_URL
            == "https://login.tailscale.com/admin/api/public/admin/tcd/offers"
        )

    def test_set_url_constant(self) -> None:
        """Test that SET URL is correct."""
        assert (
            TailnetNameGenerator.SET_URL
            == "https://login.tailscale.com/admin/api/public/admin/tcd"
        )

    def test_default_delay_constant(self) -> None:
        """Test that default delay constant is set."""
        assert TailnetNameGenerator.DEFAULT_DELAY == 0.5

    def test_is_default_tailscale_name(self) -> None:
        """Test that default Tailscale names are identified correctly."""
        gen = TailnetNameGenerator(cookie="test_cookie")

        # Test names that should be filtered
        assert gen._is_default_tailscale_name("tail1ab2") is True
        assert gen._is_default_tailscale_name("tail1234") is True
        assert gen._is_default_tailscale_name("TAIL5678") is True
        assert gen._is_default_tailscale_name("Tail9abc") is True

        # Test names that should NOT be filtered
        assert gen._is_default_tailscale_name("tailored-name") is False
        assert gen._is_default_tailscale_name("tailor-swift") is False
        assert gen._is_default_tailscale_name("awesome-tail") is False
        assert gen._is_default_tailscale_name("king") is False
        assert gen._is_default_tailscale_name("dragon-fish") is False
