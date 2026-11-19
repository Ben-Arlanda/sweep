"""Recipe Images (slice 4f, ADR 0027): the committed files and credits, and the API."""

import uuid

import httpx
import pytest
from PIL import Image
from sqlalchemy import Engine, text

from app.data.recipe_images import (
    ALLOWED,
    FILES,
    SIZES,
    RecipeImage,
    file_name,
    load_recipe_images,
)
from app.data.recipes import load_seed_recipes
from app.db import make_engine, make_sessionmaker
from app.services import adaptations
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household
from tests.test_recipes import PASTA, STIR_FRY

pytestmark = pytest.mark.anyio

RECORDS = load_recipe_images()
PASTA_PHOTO = RecipeImage(
    slug="tomato-pasta",
    author="Joe Mahoney",
    licence="CC BY 2.0",
    licence_url="https://creativecommons.org/licenses/by/2.0",
    source_url="https://commons.wikimedia.org/wiki/File:Pasta.jpg",
    seen="Spaghetti in a red tomato sauce.",
    dish="yes",
)


def test_every_credit_is_for_a_seed_recipe_with_an_open_licence() -> None:
    slugs = {r.slug for r in load_seed_recipes()}
    assert {r.slug for r in RECORDS} <= slugs
    assert all(r.licence.startswith(ALLOWED) for r in RECORDS)
    assert all(r.dish in ("yes", "close") for r in RECORDS)
    assert len({r.source_url for r in RECORDS}) == len(RECORDS)  # no photo used twice
    assert len({r.slug for r in RECORDS}) == len(RECORDS)


def test_every_image_file_is_small_4_by_3_webp_with_a_credit() -> None:
    expected = {file_name(r.slug, size) for r in RECORDS for size in SIZES}
    assert {p.name for p in FILES.glob("*")} == expected  # nothing missing, nothing extra
    for record in RECORDS:
        for size, (width, most) in SIZES.items():
            path = FILES / file_name(record.slug, size)
            assert path.stat().st_size <= most, path.name
            with Image.open(path) as image:
                assert (image.format, image.size) == ("WEBP", (width, width * 3 // 4))


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
        "thumb_url": "/static/recipes/tomato-pasta-360.webp",
        "hero_url": "/static/recipes/tomato-pasta-960.webp",
        "author": "Joe Mahoney",
        "licence": "CC BY 2.0",
        "licence_url": "https://creativecommons.org/licenses/by/2.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Pasta.jpg",
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


async def test_the_api_serves_the_image_files(client: httpx.AsyncClient) -> None:
    files = sorted(FILES.glob("*.webp"))
    assert files, "no Recipe Images written yet"
    response = await client.get(f"/static/recipes/{files[0].name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert "max-age" in response.headers.get("cache-control", "")
    assert (await client.get("/static/recipes/nope.webp")).status_code == 404
    assert (await client.get("/static/recipes/../recipe_images.json")).status_code == 404
