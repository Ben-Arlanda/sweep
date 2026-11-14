# Sweep API

FastAPI backend. Run from this folder:

```bash
docker compose up -d                  # Postgres on localhost:5433 (from the repo root)
docker compose exec db createdb -U sweep sweep_test   # once, for the tests
uv sync                               # install dependencies
uv run alembic upgrade head           # apply migrations (also loads the Ingredient list)
uv run python -m app.seed_recipes     # load Seed Recipes + embed new/changed (needs VOYAGE_API_KEY)
uv run fastapi dev app/main.py        # dev server on http://localhost:8000
uv run pytest                         # tests (rebuild sweep_test from the migrations)
uv run ruff check . && uv run mypy    # lint + type check
uv run python -m evals.ingredient_parsing --llm   # ingredient-line eval (one cheap Claude call)
uv run python -m app.check_recipes                # check every Seed Recipe (free, also runs in CI)
uv run python -m evals.recipe_review --llm        # measure the AI recipe reviewer (~14 Claude calls)
```

AI keys (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`) are optional: without them, search is off
and parsing is rules-only. Tests use fakes and never call out.

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
  idempotency.py Idempotency-Key handling: retries replay, never repeat
  realtime.py    Postgres NOTIFY → listener → Hub → WebSockets (ADR 0004)
  units.py       amount parsing and unit conversion (deterministic, ADR 0003)
  seed.py        reference data loader; data/ingredients.py is the starter Ingredient list
  seed_recipes.py   loads data/recipes/*.toml (Seed Recipes) and embeds them
  llm.py         the only module that calls an LLM (Claude), with structured outputs
  embeddings.py  the only module that calls Voyage; plus a fake for tests
alembic/         database migrations
evals/           labelled datasets + scripts that score AI behaviour
```

New migration after changing `models.py`: `uv run alembic revision --autogenerate -m "what changed"`, then read the generated file before committing.
