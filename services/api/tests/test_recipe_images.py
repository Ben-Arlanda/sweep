"""Recipe Images (slice 4f, ADR 0029): the committed credits, and the API."""

import uuid

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, text

from app.data.recipe_images import RecipeImage, load_recipe_images, sized
from app.data.recipes import load_seed_recipes
from app.db import make_engine, make_sessionmaker
from app.services import adaptations
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household
from tests.test_recipes import PASTA, STIR_FRY

pytestmark = pytest.mark.anyio

RECORDS = load_recipe_images()
RAW = "https://images.unsplash.com/photo-1?ixid=M3xyz&ixlib=rb-4.1.0"
PASTA_PHOTO = RecipeImage(
    slug="tomato-pasta",
    source="unsplash",
    photo_id="abc123",
    raw_url=RAW,
    author="Ana Cook",
    author_url="https://unsplash.com/@anacook",
    photo_url="https://unsplash.com/photos/pasta-abc123",
)
UTM = "?utm_source=sweep&utm_medium=referral"


def test_every_credit_is_for_a_seed_recipe_and_a_different_photo() -> None:
    slugs = {r.slug for r in load_seed_recipes()}
    assert {r.slug for r in RECORDS} <= slugs
    assert len({r.slug for r in RECORDS}) == len(RECORDS)
    assert len({r.photo_id for r in RECORDS}) == len(RECORDS)  # no photo used twice


async def get(client: httpx.AsyncClient, issuer: FakeIssuer, path: str) -> httpx.Response:
    response = await client.get(path, headers=issuer.headers("ana"))
    assert response.status_code == 200, response.text
    return response


async def test_a_seed_recipe_with_a_photo_returns_its_files_and_credit(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA, STIR_FRY], images=[PASTA_PHOTO])
    await create_household(client, fake_issuer, "ana")
    listed = {r["title"]: r for r in (await get(client, fake_issuer, "/recipes")).json()}
    image = listed["Quick tomato pasta"]["image"]
    assert image == {
        "thumb_url": sized(RAW, 360),
        "hero_url": sized(RAW, 960),
        "author": "Ana Cook",
        "author_url": f"https://unsplash.com/@anacook{UTM}",
        "source": "Unsplash",
        "source_url": f"https://unsplash.com/{UTM}",
    }
    assert listed["Beef and broccoli stir-fry"]["image"] is None
    recipe_id = listed["Quick tomato pasta"]["id"]
    assert (await get(client, fake_issuer, f"/recipes/{recipe_id}")).json()["image"] == image

    await load([PASTA, STIR_FRY])  # the photo was rejected: the recipe goes back to art
    listed = {r["title"]: r for r in (await get(client, fake_issuer, "/recipes")).json()}
    assert listed["Quick tomato pasta"]["image"] is None


async def test_an_adaptation_has_no_photo_since_its_dish_changed(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine, database_url: str
) -> None:
    beef = PASTA_PHOTO.model_copy(update={"slug": "beef-stir-fry"})
    await load([STIR_FRY], images=[beef])
    home = await create_household(client, fake_issuer, "ana")
    with db.connect() as conn:
        parent = conn.execute(text("SELECT id FROM recipes WHERE slug = 'beef-stir-fry'")).scalar()
    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        made = await adaptations.create(
            session,
            uuid.UUID(home["household"]["id"]),
            uuid.UUID(str(parent)),
            [adaptations.SwapIn(0, "400 g firm tofu")],
        )
        await session.commit()
        made_id = made.id
    await engine.dispose()
    # The photo shows beef; the Adaptation has tofu.
    assert (await get(client, fake_issuer, f"/recipes/{made_id}")).json()["image"] is None


def test_a_credit_must_point_at_unsplash() -> None:
    fields = PASTA_PHOTO.model_dump()
    for bad in (
        {"raw_url": "https://evil.test/photo-1?ixid=x"},
        {"raw_url": "https://images.unsplash.com/photo-1"},  # ixid dropped
        {"author_url": "https://unsplash.com/@ana?x=1"},
        {"source": "wikimedia"},
    ):
        with pytest.raises(ValidationError):
            RecipeImage.model_validate(fields | bad)
