# Sweep API

FastAPI backend. Run from this folder:

```bash
docker compose up -d                  # Postgres on localhost:5433 (from the repo root)
docker compose exec db createdb -U sweep sweep_test   # once, for the tests
uv sync                               # install dependencies
uv run alembic upgrade head           # apply database migrations
uv run fastapi dev app/main.py        # dev server on http://localhost:8000
uv run pytest                         # tests (rebuild sweep_test from the migrations)
uv run ruff check . && uv run mypy    # lint + type check
```

## Layout

```
app/
  main.py        app factory, error → HTTP status mapping
  config.py      settings from env vars
  auth.py        verifies login tokens (JWTs) → Identity
  deps.py        per-request wiring: session → Identity → MemberContext
  routes/        thin HTTP layer
  services/      business rules and permissions (no HTTP; reused by the agent later)
  models.py      SQLAlchemy tables
  schemas.py     Pydantic request/response shapes (→ OpenAPI → client types)
  errors.py      domain errors raised by services
alembic/         database migrations
```

New migration after changing `models.py`: `uv run alembic revision --autogenerate -m "what changed"`, then read the generated file before committing.
