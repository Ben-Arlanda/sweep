"""Runs agent Scenarios against the real graph and records what happened (slice 8).

The same `Agent` class the HTTP routes use runs each turn, so an eval exercises the
production path: load_context → agent ⇄ tools → validate → approve → commit. Only the
edges are swapped: which database, which model, which embedder.

Two phases, kept apart on purpose:
1. Run: build the Scenario's Household, send its messages, approve or reject.
2. Collect facts: read the Proposals, recipes, Dietary Rules and Kitchen back from the
   database into plain dataclasses (`RunRecord`). Graders (evals/agent_graders.py) are
   then pure functions of those facts: no database, no async, easy to test.
"""

import hashlib
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agent.checkpoints import Checkpoints
from app.agent.model import AgentModel, ModelTurn
from app.agent.prompt import today_in_sydney
from app.auth import Identity
from app.data.diet import Diet
from app.data.recipes import load_seed_recipes
from app.db import make_engine, make_sessionmaker, sqlalchemy_url
from app.embeddings import Embedder, EmbeddingUnavailable, Purpose
from app.llm_costs import Usage
from app.models import Conversation, Ingredient, PlanMode, Proposal
from app.services import conversations, diet, households, kitchen, kitchen_match, recipes
from app.services.conversations import Agent
from app.services.diet import DietaryRules
from app.services.ingredient_lines import index_from_db

API_DIR = Path(__file__).resolve().parent.parent
# Far above a real turn: the eval measures spend itself and stops on --max-spend.
EVAL_TOKEN_BUDGET = 10_000_000

# --- Describing a Scenario -------------------------------------------------------------


@dataclass(frozen=True)
class Setup:
    """The Household a Scenario starts from. Ingredient names are starter Ingredients."""

    diets: frozenset[Diet] = frozenset()
    excluded: tuple[str, ...] = ()
    household_size: int | None = 2
    cuisines: tuple[str, ...] = ()
    # Tracked Kitchen items: name → quantity in the Ingredient's own unit (None = "some").
    kitchen: dict[str, Decimal | None] = field(default_factory=dict)
    # The "Plan my week" sheet. Days are offsets from today (0 = today); None = not used.
    mode: PlanMode | None = None
    days: tuple[int, ...] | None = None
    # Make the embedder fail this many times first (a Voyage outage).
    embedder_failures: int = 0


@dataclass(frozen=True)
class Say:
    """A Member message. `{0}`, `{1}`… become the weekday names of the chosen days."""

    text: str


@dataclass(frozen=True)
class Approve:
    pass


@dataclass(frozen=True)
class Reject:
    pass


Step = Say | Approve | Reject


# --- What a run produced ---------------------------------------------------------------


@dataclass(frozen=True)
class MealFacts:
    date: str
    recipe_id: str
    title: str
    exists: bool  # the recipe is in the Recipe Knowledge Base for this Household
    rule_breaks: tuple[str, ...]  # Dietary Rules it breaks, checked again from scratch
    to_buy: int | None  # missing Ingredients against the Kitchen (None if it doesn't exist)
    kitchen_uses: tuple[str, ...]  # Tracked Kitchen items it uses


@dataclass(frozen=True)
class ProposalFacts:
    status: str
    meals: tuple[MealFacts, ...]
    dropped: tuple[str, ...]  # meals validate had to take out after the replans ran out
    list_additions: int


@dataclass(frozen=True)
class TurnFacts:
    """One Member message and what streamed back."""

    said: str
    reply: str
    tools: tuple[str, ...]
    replans: int
    error: str | None
    seconds: float


@dataclass(frozen=True)
class RunRecord:
    scenario: str
    model: str
    turns: tuple[TurnFacts, ...]
    proposals: tuple[ProposalFacts, ...]  # oldest first
    chosen_days: tuple[str, ...] | None  # ISO dates, when the Scenario picked days
    today: str  # ISO date the run used as "today" (Sydney)
    usages: tuple[Usage, ...]  # one per model call
    seconds: float
    # Part of `seconds` spent waiting on Voyage (our free tier's rate limit, not the agent).
    embedding_seconds: float = 0.0
    session_id: str = ""  # the Conversation id: its Langfuse session, when tracing is on
    planner: str = "agent"  # or "baseline" (evals/baseline.py)
    crashed: str | None = None  # the harness itself failed (not the agent)

    @property
    def final(self) -> ProposalFacts | None:
        return self.proposals[-1] if self.proposals else None

    @property
    def tool_calls(self) -> tuple[str, ...]:
        return tuple(name for turn in self.turns for name in turn.tools)

    @property
    def replans(self) -> int:
        return sum(turn.replans for turn in self.turns)


# --- Edges: recording model, embedders ------------------------------------------------


class RecordingModel:
    """Passes calls through to the real model and keeps each turn's usage."""

    def __init__(self, inner: AgentModel) -> None:
        self.inner = inner
        self.name = inner.name
        self.parameters = inner.parameters
        self.turns: list[ModelTurn] = []

    async def respond(
        self,
        system: str,
        tools: Sequence[dict[str, Any]],
        messages: Sequence[dict[str, Any]],
        on_text: Callable[[str], None],
    ) -> ModelTurn:
        turn = await self.inner.respond(system, tools, messages, on_text)
        self.turns.append(turn)
        return turn


class CachedEmbedder:
    """Remembers search-text vectors on disk, keyed by model + purpose + text.

    Voyage's free tier allows 3 requests a minute; Sonnet tends to write the same
    searches again ("quick gluten free dinner"), so repeats and re-runs are answered
    from the cache. Changing the model changes the key, so nothing goes stale silently.
    """

    def __init__(self, inner: Embedder, path: Path) -> None:
        self.inner = inner
        self.model = inner.model
        self.path = path
        self.hits = 0
        self.misses = 0
        self.seconds = 0.0  # time spent waiting on the real embedder (rate limits included)
        self._cache: dict[str, list[float]] = json.loads(path.read_text()) if path.exists() else {}

    def _key(self, text: str, purpose: Purpose) -> str:
        return hashlib.sha256(f"{self.model}\n{purpose}\n{text}".encode()).hexdigest()

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        keys = [self._key(t, purpose) for t in texts]
        missing = [t for t, k in zip(texts, keys, strict=True) if k not in self._cache]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)
        if missing:
            started = time.monotonic()
            vectors = await self.inner.embed(missing, purpose)
            self.seconds += time.monotonic() - started
            for t, v in zip(missing, vectors, strict=True):
                self._cache[self._key(t, purpose)] = v
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._cache))
        return [self._cache[k] for k in keys]


class FlakyEmbedder:
    """Fails the first `failures` calls, then behaves: a short Voyage outage."""

    def __init__(self, inner: Embedder, failures: int) -> None:
        self.inner = inner
        self.model = inner.model
        self.failures = failures

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        if self.failures > 0:
            self.failures -= 1
            raise EmbeddingUnavailable("injected by the eval")
        return await self.inner.embed(texts, purpose)


# --- The eval database ------------------------------------------------------------------


@dataclass
class EvalDatabase:
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    checkpoints: Checkpoints


@asynccontextmanager
async def open_database(database_url: str) -> AsyncIterator[EvalDatabase]:
    """Connections to an already-migrated database with recipes loaded."""
    engine = make_engine(database_url)
    checkpoints = Checkpoints(database_url)
    try:
        await checkpoints.setup()  # before any turn: see app/agent/checkpoints.py
        yield EvalDatabase(engine, make_sessionmaker(engine), checkpoints)
    finally:
        await checkpoints.close()
        await engine.dispose()


async def copy_recipe_embeddings(source_url: str, target: EvalDatabase, model: str) -> int:
    """Copy recipe vectors from the dev database, matched by slug, so building the eval
    database costs no Voyage calls. Only vectors of the same text (same content hash)
    are copied: a recipe whose text changed simply isn't searchable until re-embedded."""
    source = make_engine(source_url)
    try:
        async with source.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT r.slug, e.content_hash, e.embedding::text FROM recipe_embeddings e "
                        "JOIN recipes r ON r.id = e.recipe_id "
                        "WHERE e.model = :model AND r.slug IS NOT NULL"
                    ),
                    {"model": model},
                )
            ).all()
    finally:
        await source.dispose()
    async with target.engine.begin() as conn:
        await conn.execute(text("DELETE FROM recipe_embeddings WHERE model = :m"), {"m": model})
        copied = 0
        for slug, content_hash, vector in rows:
            result = await conn.execute(
                text(
                    "INSERT INTO recipe_embeddings (recipe_id, model, content_hash, embedding) "
                    "SELECT id, :model, :hash, CAST(:vector AS vector) FROM recipes "
                    "WHERE slug = :slug"
                ),
                {"model": model, "hash": content_hash, "vector": vector, "slug": slug},
            )
            copied += result.rowcount
    return copied


def prepare_eval_database(eval_url: str, dev_url: str, embedding_model: str) -> None:
    """Make `sweep_eval` ready for a run: create it if needed, migrate it, and empty it
    of Households and saved conversations. Recipes and vectors are loaded separately
    (`load_recipes`). No API calls."""
    *server, name = sqlalchemy_url(eval_url).rsplit("/", 1)
    admin = create_engine(f"{server[0]}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()

    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(eval_url))
    command.upgrade(config, "head")

    engine = create_engine(sqlalchemy_url(eval_url))
    with engine.begin() as conn:
        # Households cascade to everything they own; checkpoints aren't linked by key.
        conn.execute(text("DELETE FROM households"))
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            if conn.scalar(text("SELECT to_regclass(:t)"), {"t": table}):
                conn.execute(text(f"TRUNCATE {table}"))
    engine.dispose()


async def load_recipes(db: EvalDatabase, dev_url: str, embedding_model: str) -> tuple[int, int]:
    """Seed Recipes from the files (same as the app), vectors copied from dev.
    Returns (recipes loaded, vectors copied)."""
    async with db.sessionmaker() as session:
        report = await recipes.upsert_seed_recipes(
            session, load_seed_recipes(), await index_from_db(session)
        )
        await session.commit()
    copied = await copy_recipe_embeddings(dev_url, db, embedding_model)
    return report.loaded, copied


# --- Running one Scenario ---------------------------------------------------------------


async def _ingredient_ids(session: AsyncSession, names: Sequence[str]) -> dict[str, uuid.UUID]:
    if not names:
        return {}
    rows = await session.execute(
        select(Ingredient.name, Ingredient.id).where(
            Ingredient.name.in_(names), Ingredient.household_id.is_(None)
        )
    )
    found = {name: ingredient_id for name, ingredient_id in rows}
    unknown = set(names) - set(found)
    if unknown:
        raise ValueError(f"not starter Ingredients: {sorted(unknown)}")
    return found


async def build_household(
    session: AsyncSession, setup: Setup, today: date
) -> tuple[Identity, households.MemberContext, uuid.UUID]:
    """A fresh Household as the Scenario describes, and a Conversation for it."""
    identity = Identity(issuer="https://eval.sweep", subject=f"eval-{uuid.uuid4().hex[:12]}")
    ctx = await households.create_household(session, identity, "Eval House", "Eval")
    hid = ctx.household.id
    if setup.diets or setup.excluded:
        ids = await _ingredient_ids(session, setup.excluded)
        await diet.set_rules(session, hid, DietaryRules(setup.diets, frozenset(ids.values())))
    await diet.set_preferences(session, hid, setup.household_size, setup.cuisines)
    for name, ingredient_id in (await _ingredient_ids(session, list(setup.kitchen))).items():
        await kitchen.set_tracked(session, ctx, ingredient_id, setup.kitchen[name])
    days = [today + timedelta(days=d) for d in setup.days] if setup.days is not None else None
    conversation = await conversations.create(session, ctx, setup.mode, days)
    return identity, ctx, conversation.id


def list_days(days: Sequence[date]) -> str:
    """ "Tue 17, Wed 18 and Thu 19 Nov", as the app writes it (starters.ts listDays)."""
    parts = []
    for i, d in enumerate(days):
        month_ends = i == len(days) - 1 or days[i + 1].month != d.month
        parts.append(f"{d:%a} {d.day}" + (f" {d:%b}" if month_ends else ""))
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def words(step: Say, days: Sequence[date] | None) -> str:
    """`{0}`, `{1}`… → weekday names of the chosen days; `{days}` → the app's day list."""
    chosen = list(days or ())
    return step.text.format(*(f"{d:%A}" for d in chosen), days=list_days(chosen) if chosen else "")


async def _say(agent: Agent, conversation: Conversation, words: str) -> TurnFacts:
    started = time.monotonic()
    reply, tools, replans, error = [], [], 0, None
    async for event in agent.run_turn(conversation, words):
        kind = event["type"]
        if kind == "text":
            reply.append(event["text"])
        elif kind == "tool":
            tools.append(event["name"])
        elif kind == "replan":
            replans += 1
        elif kind == "error":
            error = event["message"]
    return TurnFacts(
        said=words,
        reply="".join(reply),
        tools=tuple(tools),
        replans=replans,
        error=error,
        seconds=time.monotonic() - started,
    )


async def _decide(agent: Agent, conversation: Conversation, action: str) -> None:
    waiting = await agent.waiting_on(conversation.id)
    if waiting is None:
        return  # nothing to decide: the grader will report the missing Proposal
    decision: dict[str, Any] = {"action": action}
    if action == "approve":
        decision |= {"keep_meals": None, "keep_additions": None}  # keep everything
    await agent.decide(conversation, uuid.UUID(waiting), decision)


async def collect_proposals(
    session: AsyncSession, ctx: households.MemberContext, conversation_id: uuid.UUID
) -> tuple[ProposalFacts, ...]:
    rows = (
        await session.execute(
            select(Proposal)
            .where(Proposal.conversation_id == conversation_id)
            .order_by(Proposal.created_at)
        )
    ).scalars()
    rules = await diet.get_rules(session, ctx.household.id)
    snap = await kitchen_match.snapshot(session, ctx)
    out = []
    for row in rows:
        payload = row.payload
        ids = [m["recipe_id"] for m in payload["meals"]]
        found = await recipes.get_many(session, ctx.household.id, ids)
        meals = []
        for m in payload["meals"]:
            recipe = found.get(m["recipe_id"])
            lines = kitchen_match.lines_of(recipe) if recipe is not None else []
            meals.append(
                MealFacts(
                    date=m["date"],
                    recipe_id=m["recipe_id"],
                    title=m["title"],
                    exists=recipe is not None,
                    rule_breaks=(tuple(diet.check_recipe(recipe, rules).breaks) if recipe else ()),
                    to_buy=(len(kitchen_match.match(lines, snap).missing) if recipe else None),
                    kitchen_uses=tuple(kitchen_match.uses(lines, snap)),
                )
            )
        out.append(
            ProposalFacts(
                status=row.status.value,
                meals=tuple(meals),
                dropped=tuple(payload.get("dropped", [])),
                list_additions=len(payload.get("list_additions", [])),
            )
        )
    return tuple(out)


async def run_scenario(
    db: EvalDatabase,
    model: AgentModel,
    embedder: Embedder,
    name: str,
    setup: Setup,
    steps: Sequence[Step],
    trace_metadata: dict[str, Any] | None = None,
) -> RunRecord:
    """Run one Scenario once. Never raises for the agent's mistakes: they're the result."""
    started = time.monotonic()
    embedded_before = embedder.seconds if isinstance(embedder, CachedEmbedder) else 0.0
    recording = RecordingModel(model)
    cached = embedder
    if setup.embedder_failures:
        embedder = FlakyEmbedder(embedder, setup.embedder_failures)
    agent = Agent(
        recording, db.checkpoints, db.engine, db.sessionmaker, embedder, EVAL_TOKEN_BUDGET
    )
    # Tags stay low-cardinality (filterable); run-specific values go in metadata.
    agent.trace_tags = ["eval", f"scenario:{name}"]
    agent.trace_metadata = {"scenario": name, **(trace_metadata or {})}
    today = today_in_sydney()
    async with db.sessionmaker() as session:
        identity, _, conversation_id = await build_household(session, setup, today)
        await session.commit()
        conversation = await session.get_one(Conversation, conversation_id)
        days = conversation.plan_days

    turns: list[TurnFacts] = []
    crashed = None
    try:
        for step in steps:
            if isinstance(step, Say):
                turns.append(await _say(agent, conversation, words(step, days)))
            else:
                action = "approve" if isinstance(step, Approve) else "reject"
                await _decide(agent, conversation, action)
    except Exception as error:  # the harness or a decision failed: record it, keep going
        crashed = f"{type(error).__name__}: {error}"

    async with db.sessionmaker() as session:
        ctx = await households.get_member_context(session, identity)
        proposals = await collect_proposals(session, ctx, conversation_id)
    return RunRecord(
        scenario=name,
        model=model.name,
        turns=tuple(turns),
        proposals=proposals,
        chosen_days=tuple(d.isoformat() for d in days) if days is not None else None,
        today=today.isoformat(),
        usages=tuple(t.usage for t in recording.turns),
        session_id=str(conversation_id),
        seconds=time.monotonic() - started,
        embedding_seconds=(
            cached.seconds - embedded_before if isinstance(cached, CachedEmbedder) else 0.0
        ),
        crashed=crashed,
    )
