"""Load the Seed Recipes and embed anything new or changed: `uv run python -m app.seed_recipes`.

`--no-embed` loads the recipes only (no API calls): they show up when browsing, and
search finds them once a later run embeds them.

Not run from migrations (unlike Ingredients): embedding calls a paid outside API, and
migrations must work offline and in CI. Safe to run any number of times. Recipes whose
text hasn't changed are not re-embedded, so a re-run costs nothing.
"""

import argparse
import asyncio
import sys

from app.config import settings
from app.data.recipes import load_seed_recipes
from app.db import make_engine, make_sessionmaker
from app.embeddings import VoyageEmbedder
from app.services import recipes
from app.services.ingredient_lines import index_from_db


async def main(embed: bool = True) -> int:
    engine = make_engine(settings.database_url)
    async with make_sessionmaker(engine)() as session:
        report = await recipes.upsert_seed_recipes(
            session, load_seed_recipes(), await index_from_db(session)
        )
        print(f"{report.loaded} Seed Recipes loaded ({report.lines} lines)")
        print(f"{report.removed} removed (no longer in the seed files)")
        for line in report.needs_review:
            print(f"  needs review: {line}")
        # Save the recipes now, so a failed embedding run doesn't lose them. Embedding
        # is resumable: the next run only embeds what's still missing.
        await session.commit()

        if not embed:
            print("--no-embed: skipping embeddings (new recipes are browsable, not searchable)")
        elif settings.voyage_api_key is None:
            print("VOYAGE_API_KEY not set: skipping embeddings (search stays off)")
        else:
            embedder = VoyageEmbedder(
                settings.voyage_api_key.get_secret_value(),
                settings.embedding_model,
                # Small batches and patient retries fit Voyage's free-tier limit
                # (3 requests / 10k tokens a minute) as well as the normal one.
                batch=40,
                retries=6,
                backoff=20.0,
            )
            total = 0
            while count := await recipes.embed_missing(session, embedder, limit=40):
                await session.commit()  # keep each chunk, in case a later one fails
                total += count
                print(f"  {total} embedded…")
            print(f"{total} recipes embedded with {embedder.model}")
    await engine.dispose()
    return 1 if report.needs_review else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-embed", action="store_true", help="load recipes without embedding")
    sys.exit(asyncio.run(main(embed=not parser.parse_args().no_embed)))
