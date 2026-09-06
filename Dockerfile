FROM python:3.14-alpine3.24 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --all-extras --no-install-project --no-dev --no-editable

COPY pyproject.toml uv.lock LICENSE README.md ./
COPY src/ ./src/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras --no-dev --no-editable


FROM python:3.14-alpine3.24
LABEL org.opencontainers.image.title="Tailnet Name Generator" \
      org.opencontainers.image.description="Async brute force generator for Tailscale tailnet fun names with advanced filtering" \
      org.opencontainers.image.url="https://github.com/mhajder/tailnet-name-generator" \
      org.opencontainers.image.source="https://github.com/mhajder/tailnet-name-generator" \
      org.opencontainers.image.vendor="Mateusz Hajder" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache ca-certificates \
    && addgroup -g 1000 appuser \
    && adduser -D -u 1000 -G appuser appuser

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

WORKDIR /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["ts-name"]
