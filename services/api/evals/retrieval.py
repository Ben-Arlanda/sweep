"""Retrieval evals: which search method finds the right recipes? (slice 9)

    uv run python -m evals.retrieval                 # R1, R2, R3 on dev and test
    uv run python -m evals.retrieval --rerank        # also R4 (Voyage rerank, cached)
    uv run python -m evals.retrieval --pool          # labelling worksheet, no scores

The Retrieval Set (`retrieval_queries.jsonl`, see CONTEXT.md) is ~50 searches with the
Seed Recipes that should come back, by slug. The queries were written before any method
ran; each has an `intent` line, and labels follow the intent, not what a method found.

Methods, all after the same SQL filters (none here: the eval Household has no Rules):
- R1 meaning: Voyage query vector, pgvector cosine distance (the product today).
- R2 keyword: Postgres full-text search, any word, ts_rank_cd.
- R3 hybrid: reciprocal rank fusion of R1's and R2's top 30.
- R4 rerank: Voyage's reranker re-orders R3's top 30.

Scores, per query, then averaged:
- recall@10: share of the relevant recipes in the top 10. "Did it find them?" Broad
  queries ("cosy winter dinner": 42 relevant) can't score above 10/42, so also:
- P@10: share of the top 10 that are relevant. "Is the first screen any good?"
- MRR@10: 1 / rank of the first relevant recipe (0 if none in the top 10). "Was the
  first good answer near the top?" The Recipes tab shows ~8 results.
- recall@60: recipes_from_kitchen takes the top 60 and lets Kitchen Match re-order them.
- unjudged@10: top-10 recipes nobody labelled (pooling missed them). Should be 0; if not,
  run --pool again and label them, or the method is scored unfairly.

Latency: each method timed 5 times per query on local Postgres, query vectors already
cached, so R1's time is the database's, not Voyage's. Free apart from R4 and the first
query embeddings (one Voyage call for all queries, then cached in evals/.cache/).

Pooled labelling: --pool writes evals/.cache/pool.json, every method's top 20 plus every
recipe that uses an Ingredient the query names, minus what's already judged. Label those
(add slugs to `relevant`; everything looked at goes in `judged`) and re-run.
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.embeddings import Embedder, VoyageEmbedder
from app.models import Recipe, RecipeIngredient, RecipeKind
from app.services import ingredients, recipes
from evals.agent_harness import CachedEmbedder, load_recipes, open_database, prepare_eval_database

EVALS = Path(__file__).resolve().parent
QUERIES = EVALS / "retrieval_queries.jsonl"
POOL = EVALS / ".cache" / "pool.json"
KINDS = ("dish", "ingredient", "mood", "words", "spelling", "negation", "style")
FUSE_DEPTH = 30  # how many of R1's and R2's results R3 fuses, and R4 reranks
POOL_DEPTH = 20
DEEP = 60  # recipes_from_kitchen's CANDIDATES
TIMINGS = 5
NO_FILTERS = recipes.RecipeFilters()


@dataclass(frozen=True)
class Query:
    id: str
    query: str
    kind: str
    split: str
    intent: str
    relevant: frozenset[str] = frozenset()
    judged: frozenset[str] = frozenset()  # every slug looked at, relevant or not
    labelled_by: str = ""  # "rule" (SQL over the lines: repeatable) or "hand"


def load_queries(path: Path = QUERIES) -> list[Query]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            row["relevant"] = frozenset(row.get("relevant", ()))
            row["judged"] = frozenset(row.get("judged", ())) | row["relevant"]
            out.append(Query(**row))
    return out


# --- Scores (pure) ----------------------------------------------------------------------


def recall_at(ranked: Sequence[str], relevant: frozenset[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def precision_at(ranked: Sequence[str], relevant: frozenset[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / k


def reciprocal_rank(ranked: Sequence[str], relevant: frozenset[str], k: int = 10) -> float:
    for rank, slug in enumerate(ranked[:k], start=1):
        if slug in relevant:
            return 1 / rank
    return 0.0


@dataclass
class Scored:
    query_id: str
    kind: str
    split: str
    recall10: float
    p10: float
    mrr10: float
    recall60: float
    unjudged10: int
    top: list[str]
    ms: list[float] = field(default_factory=list)


def score(query: Query, ranked: Sequence[str]) -> Scored:
    return Scored(
        query.id,
        query.kind,
        query.split,
        recall_at(ranked, query.relevant, 10),
        precision_at(ranked, query.relevant, 10),
        reciprocal_rank(ranked, query.relevant),
        recall_at(ranked, query.relevant, DEEP),
        sum(1 for s in ranked[:10] if s not in query.judged),
        list(ranked[:10]),
    )


def percentile(values: Sequence[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


def summarise(rows: Sequence[Scored]) -> dict[str, float]:
    ms = [m for r in rows for m in r.ms]
    return {
        "queries": len(rows),
        "recall10": statistics.mean(r.recall10 for r in rows) if rows else 0.0,
        "p10": statistics.mean(r.p10 for r in rows) if rows else 0.0,
        "mrr10": statistics.mean(r.mrr10 for r in rows) if rows else 0.0,
        "recall60": statistics.mean(r.recall60 for r in rows) if rows else 0.0,
        "unjudged10": sum(r.unjudged10 for r in rows),
        "p50_ms": percentile(ms, 0.5) if ms else 0.0,
        "p95_ms": percentile(ms, 0.95) if ms else 0.0,
    }


# --- Methods ----------------------------------------------------------------------------

# A method: (session, query text, how many) → slugs, best first.
Method = Callable[[AsyncSession, str, int], Awaitable[list[str]]]
HOUSEHOLD = uuid.uuid4()  # sees every Seed Recipe, owns nothing


def _slugs(found: Sequence[tuple[Recipe, float]]) -> list[str]:
    return [r.slug for r, _ in found if r.slug]


def methods(embedder: Embedder, reranker: "Reranker | None") -> dict[str, Method]:
    async def r1(session: AsyncSession, text: str, limit: int) -> list[str]:
        return _slugs(await recipes.search(session, HOUSEHOLD, embedder, text, NO_FILTERS, limit))

    async def r2(session: AsyncSession, text: str, limit: int) -> list[str]:
        return _slugs(await recipes.keyword_search(session, HOUSEHOLD, text, NO_FILTERS, limit))

    async def r3(session: AsyncSession, text: str, limit: int) -> list[str]:
        # Always the same depth: the order must not depend on how many results are asked for.
        meaning = await r1(session, text, FUSE_DEPTH)
        keyword = await r2(session, text, FUSE_DEPTH)
        return [slug for slug, _ in recipes.fuse([meaning, keyword])][:limit]

    found: dict[str, Method] = {"R1": r1, "R2": r2, "R3": r3}
    if reranker is not None:
        rerank_with = reranker

        async def r4(session: AsyncSession, text: str, limit: int) -> list[str]:
            shortlist = await r3(session, text, FUSE_DEPTH)
            docs = await _documents(session, shortlist)
            order = await rerank_with.rerank(text, [docs[s] for s in shortlist])
            reranked = [shortlist[i] for i in order]
            # Below the reranked 30, R3's order (so recall@60 stays comparable).
            rest = [s for s in await r3(session, text, limit) if s not in set(reranked)]
            return (reranked + rest)[:limit]

        found["R4"] = r4
    return found


async def _documents(session: AsyncSession, slugs: Sequence[str]) -> dict[str, str]:
    rows = (await session.execute(select(Recipe).where(Recipe.slug.in_(slugs)))).scalars()
    return {r.slug: recipes.embedding_text(r) for r in rows if r.slug}


class Reranker(Protocol):
    """Anything that orders documents for a query: positions, best first."""

    async def rerank(self, query: str, documents: Sequence[str]) -> list[int]: ...


# --- Running ----------------------------------------------------------------------------


async def run_method(
    session: AsyncSession, method: Method, queries: Sequence[Query]
) -> list[Scored]:
    out = []
    for q in queries:
        ranked = await method(session, q.query, DEEP)
        row = score(q, ranked)
        for _ in range(TIMINGS):
            started = time.perf_counter()
            await method(session, q.query, DEEP)
            row.ms.append((time.perf_counter() - started) * 1000)
        out.append(row)
    return out


async def named_ingredient_recipes(session: AsyncSession, text: str) -> set[str]:
    """Seed Recipes using an Ingredient the query (or one of its words) names: the
    pooling safety net for recipes no method ranks highly."""
    words = text.lower().split()
    names = {text, *words, *(" ".join(p) for p in zip(words, words[1:], strict=False))}
    ids = set()
    for name in names:
        found = await ingredients.resolve(session, HOUSEHOLD, name, create=False)
        if found is not None:
            ids.add(found.id)
    if not ids:
        return set()
    rows = await session.execute(
        select(Recipe.slug)
        .join(RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id)
        .where(RecipeIngredient.ingredient_id.in_(ids), Recipe.kind == RecipeKind.SEED)
    )
    return {slug for slug in rows.scalars() if slug}


async def pool(
    session: AsyncSession, all_methods: dict[str, Method], queries: Sequence[Query]
) -> dict[str, Any]:
    titles = {
        slug: title for slug, title in await session.execute(select(Recipe.slug, Recipe.title))
    }
    sheet: dict[str, Any] = {}
    for q in queries:
        candidates: set[str] = await named_ingredient_recipes(session, q.query)
        for method in all_methods.values():
            candidates |= set(await method(session, q.query, POOL_DEPTH))
        new = sorted(candidates - q.judged)
        if new:
            sheet[q.id] = {
                "query": q.query,
                "intent": q.intent,
                "to_judge": {s: titles.get(s, "?") for s in new},
            }
    return sheet


def print_table(results: dict[str, list[Scored]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for split in ("dev", "test", "all"):
        print(
            f"\n{split.upper():5} {'recall@10':>10} {'P@10':>6} {'MRR@10':>8} {'recall@60':>10} "
            f"{'unjudged':>9} {'p50 ms':>8} {'p95 ms':>8}"
        )
        report[split] = {}
        for name, rows in results.items():
            chosen = [r for r in rows if split == "all" or r.split == split]
            s = summarise(chosen)
            report[split][name] = s
            print(
                f"{name:5} {s['recall10']:>10.3f} {s['p10']:>6.3f} {s['mrr10']:>8.3f} "
                f"{s['recall60']:>10.3f} "
                f"{s['unjudged10']:>9} {s['p50_ms']:>8.1f} {s['p95_ms']:>8.1f}"
            )
    print("\nBy kind (all queries), recall@10 / P@10 / MRR@10:")
    print(f"{'kind':11}" + "".join(f"{n:>20}" for n in results))
    report["by_kind"] = {}
    for kind in KINDS:
        cells = []
        report["by_kind"][kind] = {}
        for name, rows in results.items():
            s = summarise([r for r in rows if r.kind == kind])
            report["by_kind"][kind][name] = s
            cells.append(f"{s['recall10']:.2f} / {s['p10']:.2f} / {s['mrr10']:.2f}")
        print(f"{kind:11}" + "".join(f"{c:>20}" for c in cells))
    return report


async def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rerank", action="store_true", help="also R4 (Voyage rerank)")
    parser.add_argument("--pool", action="store_true", help="write the labelling worksheet")
    args = parser.parse_args(argv)

    voyage_key = settings.voyage_api_key
    if voyage_key is None:
        print("VOYAGE_API_KEY must be set in services/api/.env")
        return 2
    queries = load_queries()
    voyage = VoyageEmbedder(
        voyage_key.get_secret_value(), settings.embedding_model, retries=6, backoff=20.0
    )
    embedder = CachedEmbedder(voyage, EVALS / ".cache" / f"queries-{voyage.model}.json")
    await embedder.embed([q.query for q in queries], "query")  # one call, then cached
    reranker = None
    if args.rerank:
        from evals.retrieval_rerank import VoyageReranker

        reranker = VoyageReranker(voyage_key.get_secret_value())

    prepare_eval_database(
        settings.eval_database_url, settings.database_url, settings.embedding_model
    )
    async with open_database(settings.eval_database_url) as db:
        loaded, vectors = await load_recipes(db, settings.database_url, settings.embedding_model)
        print(f"sweep_eval: {loaded} recipes, {vectors} vectors. {len(queries)} queries.")
        all_methods = methods(embedder, reranker)
        async with db.sessionmaker() as session:
            if args.pool:
                sheet = await pool(session, all_methods, queries)
                POOL.parent.mkdir(parents=True, exist_ok=True)
                POOL.write_text(json.dumps(sheet, indent=1))
                count = sum(len(v["to_judge"]) for v in sheet.values())
                print(f"{count} recipes to judge across {len(sheet)} queries → {POOL}")
                return 0
            unlabelled = [q.id for q in queries if not q.relevant]
            if unlabelled:
                print(f"Not labelled yet: {', '.join(unlabelled)}. Run --pool and label them.")
                return 1
            results = {
                name: await run_method(session, m, queries) for name, m in all_methods.items()
            }
    report = print_table(results)
    if reranker is not None:
        print(f"\nVoyage rerank: {reranker.calls} calls, {reranker.tokens} tokens (rest cached).")
    stamp = f"{datetime.now(UTC):%Y%m%d-%H%M%S}"
    out = EVALS / "results" / f"{stamp}-retrieval.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "summary": report,
                "queries": {n: [asdict(r) for r in rows] for n, rows in results.items()},
            },
            indent=1,
        )
    )
    print(f"\n→ {out.relative_to(EVALS.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
