# The Sweep API as one container (beta hosting on Railway, ADR 0034).
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PYTHONUNBUFFERED=1

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"
# Runs as root: Railway volumes (Member photos) are root-owned, so a non-root user can't write.

# Railway sets PORT; 8000 locally.
CMD ["sh", "-c", "fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}"]
