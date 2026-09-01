"""Integration tests for the CLI."""

from click.testing import CliRunner

from ts_name.cli import main


class TestCLI:
    """Tests for the command-line interface."""

    def test_cli_requires_cookie_search(self) -> None:
        """Test that search command requires a cookie."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "cookie" in result.output.lower() or "--cookie" in result.output

    def test_cli_help(self) -> None:
        """Test that help output works."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()
        assert "claim" in result.output.lower()

    def test_cli_search_help(self) -> None:
        """Test that search subcommand help works."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "cookie" in result.output.lower()
        assert "terms" in result.output.lower()

    def test_cli_search_term_options(self) -> None:
        """Test that term options are available in search."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert "TERMS" in result.output
        assert "--any" in result.output

    def test_cli_search_length_options(self) -> None:
        """Test that length options are available in search."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert "-m" in result.output or "--max-length" in result.output
        assert "--min-length" in result.output

    def test_cli_search_any_option(self) -> None:
        """Test that the any option is available in search."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert "--any" in result.output
        assert "alternatives" in result.output.lower()

    def test_cli_search_limit_option(self) -> None:
        """Test that limit option is available in search."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert "-l" in result.output or "--limit" in result.output

    def test_cli_search_request_limit_option(self) -> None:
        """Test that search shows its request limit option."""
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert "--max-requests" in result.output
        assert "--forever" in result.output

    def test_cli_claim_help(self) -> None:
        """Test that claim command help works."""
        runner = CliRunner()
        result = runner.invoke(main, ["claim", "--help"])
        assert result.exit_code == 0
        assert "cookie" in result.output.lower()
        assert "token" in result.output.lower()
