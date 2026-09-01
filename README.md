# Tailnet Name Generator

An async Python tool for generating, brute-forcing, and setting Tailscale tailnet fun names using the frontend API. Find the perfect short and memorable name for your Tailscale network and set it with advanced filtering capabilities.

## Features

- 🚀 **Async/Await Support**: Fully asynchronous implementation for efficient API calls
- 🎯 **Advanced Filtering**: Filter by keywords and length with AND/OR logic
- 🔍 **Smart Searching**: Find the shortest tailnet names or names containing specific words
- ⚡ **Real-time Streaming**: Results appear instantly as they're found
- 🎯 **Set Names**: Easily set your preferred tailnet name once found
- 📦 **CLI Tool**: Easy-to-use command-line interface with subcommands

## Background

Tailscale allows you to assign "fun names" to your tailnet instead of the default `tail<hex>` format. These fun names are generated server-side from combinations of English words (usually animals, sometimes math-related terms).

This tool automates the search for desired tailnet names by making continuous API requests and filtering results based on your criteria.

**Reference**: [Bruteforcing tailnet "fun names"](https://yousefamar.com/memo/articles/hacks/tailnet-name/) by Yousef Amar

## Installation

### Requirements

- Python 3.11+
- `uv` package manager

### Setup

```bash
# Install dependencies
uv sync

# The CLI will be available as `ts-name`
```

## Usage

### Searching for Names

```bash
# Export your Tailscale cookie as an environment variable
export TAILSCALE_COOKIE="your_cookie_here"

# Find short names (max 10 characters) - results stream in real-time
ts-name search neko -m 10

# Find names containing "king"
ts-name search king

# Find names containing either "yo" or "ya"
ts-name search --any yo,ya

# Combine filters: names containing "king" AND shorter than 12 chars
ts-name search king -m 12

# Find 20 short names
ts-name search -m 8 -l 20

ts-name search neko-cat --claim
```

Use `--forever` to search without a request cap:

```bash
ts-name search neko --forever
```

### Setting a Name

Once you've found a name you like, simply copy its token from the search results and use it:

```bash
# Export your Tailscale cookie
export TAILSCALE_COOKIE="your_cookie_here"

# Set the tailnet name using the full token from search results
ts-name claim "awesome-name.ts.net/timestamp/hash"

# Or explicitly with the cookie option
ts-name claim --cookie YOUR_COOKIE "awesome-name.ts.net/timestamp/hash"
```

### Search Command Options

```
Options:
  --cookie TEXT                 Tailscale authentication cookie (or set 
                                TAILSCALE_COOKIE env var) [required]
  
  TERMS...                      Terms that must all match

  --any TEXT                    Comma-separated alternatives. One must match
  
  -m, --max-length INTEGER     Maximum length of tailnet name
  
  --min-length INTEGER         Minimum length of tailnet name
  
  
  -l, --limit INTEGER          Maximum number of results to return
                               [default: 1]
  
  --max-requests INTEGER       Maximum number of API requests
                               [default: 1000]

  --forever                    Search until the result limit is reached
  
  --delay FLOAT                Delay between API requests in seconds
                               [default: 0.5]
  
  --timeout FLOAT              Request timeout in seconds
                               [default: 30.0]

  --claim                      Claim the first matching name and stop
  
  -v, --verbose                Enable verbose logging
  
  --help                       Show this message and exit.
```

## Examples

### Find the shortest names
```bash
ts-name search -m 8 -l 20
```
Searches for names with max 8 characters and returns up to 20 matches. Results stream in real-time as they're found.

### Find names with specific keywords
```bash
ts-name search king ratio
```
Finds names containing BOTH "king" AND "ratio" (AND operator is default).

### Find names with any keyword
```bash
ts-name search --any cool,awesome -l 5
```
Finds names containing either "cool" OR "awesome" and returns up to 5 matches.

### Combine length and keyword filters
```bash
ts-name search king -m 10 --min-length 5
```
Finds names containing "king" that are between 5 and 10 characters long.

### Set a tailnet name
```bash
export TAILSCALE_COOKIE="your_cookie"
# From search results, copy the full token and use it:
ts-name claim "awesome-name.ts.net/timestamp/hash"
```
Sets your tailnet name to "awesome-name". The tcd (tailnet name) is automatically extracted from the token.

### Stream real-time results
```bash
ts-name search -m 15 -l 100
```
Streams names as they're found in real-time. Stop with Ctrl+C anytime - no need to wait for all 100 to complete.

## How to Get Your Tailscale Cookie

### Getting the Cookie

1. Go to [https://login.tailscale.com/admin/dns](https://login.tailscale.com/admin/dns)
2. Open Developer Tools (F12 or right-click → Inspect)
3. Go to Network tab
4. Look for Cookie in the request headers of the page load
5. Copy its value and set it as an environment variable:
   ```bash
   export TAILSCALE_COOKIE="your_cookie_here"
   ```

⚠️ **Security Warning**: Your Tailscale cookie is sensitive. Never commit it to version control or share it publicly. Use environment variables to store it safely.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ts_name

# Run specific test file
uv run pytest tests/test_filters.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Run linting and formatting checks
prek run
```

## Performance Considerations

- **Rate Limiting**: Default 0.5s delay between requests to avoid API throttling
- **Async I/O**: Non-blocking async operations allow efficient concurrent requests
- **Memory**: Configurable with `--limit` to control result set size

## Limitations

- Requires valid Tailscale authentication
- Respects Tailscale's API rate limits
- Names are generated server-side; you can't request arbitrary names
- Once you set a tailnet name, it cannot be changed if you generated HTTPS certificates for it

## Contributing

Contributions are welcome! Please ensure:
- Code passes `prek run` checks
- New features include tests
- Documentation is updated

## License

MIT License - See [LICENSE](LICENSE) file for details

## Disclaimer

This tool is provided for educational purposes. Use responsibly and in compliance with Tailscale's terms of service. Do not spam their API or attempt to circumvent rate limiting.
