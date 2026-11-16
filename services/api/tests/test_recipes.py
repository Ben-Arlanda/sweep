"""The Recipe Knowledge Base: loading Seed Recipes, R1 search, and who can see what."""

import uuid
from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.data.recipes import SeedRecipe, load_seed_recipes
from app.db import make_engine, make_sessionmaker
from app.embeddings import HashingEmbedder
from app.main import create_app
from app.models import Course
from app.services import recipes
from app.services.ingredient_lines import index_from_db
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household

pytestmark = pytest.mark.anyio


def seed(
    slug: str,
    title: str,
    minutes: int,
    cuisine: str,
    lines: list[str],
    course: Course = Course.MAIN,
) -> SeedRecipe:
    return SeedRecipe(
        slug=slug,
        title=title,
        cuisine=cuisine,
        course=course,
        servings=4,
        minutes=minutes,
        summary=title,
        ingredients=lines,
        method=["Cook it."],
    )


CURRY = seed(
    "chicken-curry",
    "Chicken and chickpea curry",
    45,
    "indian",
    ["500 g chicken thigh", "400 g can chickpeas", "1 onion, diced", "2 tbsp vegetable oil"],
)
PASTA = seed(
    "tomato-pasta",
    "Quick tomato pasta",
    20,
    "italian",
    ["400 g pasta", "400 g can canned tomatoes", "2 cloves garlic", "50 g parmesan"],
)
PAVLOVA = seed(
    "pavlova",
    "Pavlova",
    120,
    "australian",
    ["4 egg whites", "1 cup caster sugar", "300 ml thickened cream"],
    Course.DESSERT,
)
STIR_FRY = seed(
    "beef-stir-fry",
    "Beef and broccoli stir-fry",
    25,
    "chinese",
    ["500 g beef steak", "1 broccoli", "2 tbsp soy sauce", "1 cup rice"],
)


async def get(
    client: httpx.AsyncClient, issuer: FakeIssuer, path: str, **params: Any
) -> httpx.Response:
    return await client.get(path, params=params, headers=issuer.headers("ana"))


async def test_every_seed_recipe_line_parses_and_matches(database_url: str, load: Loader) -> None:
    # The real seed files: we wrote them, so every line must parse with plain rules.
    report = await load(load_seed_recipes())
    assert report.loaded >= 150
    assert report.needs_review == []


async def test_reloading_the_seed_updates_instead_of_duplicating(db: Engine, load: Loader) -> None:
    await load([CURRY, PASTA])
    changed = CURRY.model_copy(
        update={"title": "Chicken curry", "ingredients": ["1 kg chicken thigh"]}
    )
    report = await load([changed])
    assert (report.loaded, report.removed) == (1, 1)  # pasta left the seed files
    with db.connect() as conn:
        assert conn.execute(text("SELECT title FROM recipes")).scalars().all() == ["Chicken curry"]
        lines = conn.execute(text("SELECT raw_text, base_quantity FROM recipe_ingredients")).all()
        assert [(t, float(q)) for t, q in lines] == [("1 kg chicken thigh", 1000.0)]


async def test_reembeds_only_recipes_whose_text_changed(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA])
    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        assert await recipes.embed_missing(session, HashingEmbedder()) == 0  # all up to date
        edited = CURRY.model_copy(update={"summary": "Now with spinach"})
        await recipes.upsert_seed_recipes(session, [edited, PASTA], await index_from_db(session))
        assert await recipes.embed_missing(session, HashingEmbedder()) == 1  # just the curry


async def test_embedding_can_be_done_in_chunks(database_url: str, load: Loader) -> None:
    await load([CURRY, PASTA, STIR_FRY])
    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        renamed = HashingEmbedder()
        renamed.model = "fake-hashing-v2"  # a "new model": every recipe needs a vector
        assert await recipes.embed_missing(session, renamed, limit=2) == 2
        assert await recipes.embed_missing(session, renamed, limit=2) == 1
        assert await recipes.embed_missing(session, renamed, limit=2) == 0
    await engine.dispose()


async def test_search_ranks_by_meaning_and_returns_scores(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY])
    await create_household(client, fake_issuer, "ana")

    response = await get(client, fake_issuer, "/recipes", q="beef broccoli")
    assert response.status_code == 200, response.text
    results = response.json()
    assert results[0]["title"] == "Beef and broccoli stir-fry"
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


async def test_filters_are_hard_limits_not_hints(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([CURRY, PASTA, STIR_FRY])
    await create_household(client, fake_issuer, "ana")

    quick = await get(client, fake_issuer, "/recipes", q="chicken curry", max_minutes=30)
    assert {r["title"] for r in quick.json()} == {
        "Quick tomato pasta",
        "Beef and broccoli stir-fry",
    }  # the curry is the best match but takes 45 minutes

    italian = await get(client, fake_issuer, "/recipes", q="chicken", cuisine="italian")
    assert [r["title"] for r in italian.json()] == ["Quick tomato pasta"]

    with db.connect() as conn:
        garlic = conn.execute(text("SELECT id FROM ingredients WHERE name = 'garlic'")).scalar()
    no_garlic = await get(client, fake_issuer, "/recipes", exclude_ingredient=str(garlic))
    assert [r["title"] for r in no_garlic.json()] == [
        "Beef and broccoli stir-fry",
        "Chicken and chickpea curry",
    ]


def test_a_seed_recipe_must_say_its_course() -> None:
    # Every recipe has exactly one Course; the loader refuses a recipe without one.
    fields = CURRY.model_dump(exclude={"course"})
    with pytest.raises(ValidationError):
        SeedRecipe(**fields)
    with pytest.raises(ValidationError):
        SeedRecipe(**fields, course="snack")  # type: ignore[arg-type]


def test_every_seed_file_recipe_has_a_course_and_most_are_mains() -> None:
    seeds = load_seed_recipes()
    by_course = {c: sum(s.course == c for s in seeds) for c in Course}
    assert all(by_course.values()), by_course  # every Course is used
    assert by_course[Course.MAIN] > len(seeds) / 2  # it's a dinner app


async def test_course_is_a_hard_filter_and_comes_back_on_each_recipe(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, PAVLOVA])
    await create_household(client, fake_issuer, "ana")

    browse = await get(client, fake_issuer, "/recipes", course="dessert")
    assert [(r["title"], r["course"]) for r in browse.json()] == [("Pavlova", "dessert")]

    # Search too: the curry is closer in meaning, but it isn't a dessert.
    found = await get(client, fake_issuer, "/recipes", q="chicken curry", course="dessert")
    assert [r["title"] for r in found.json()] == ["Pavlova"]

    everything = await get(client, fake_issuer, "/recipes")
    assert len(everything.json()) == 3  # no Course given: all of them
    bad = await get(client, fake_issuer, "/recipes", course="snack")
    assert bad.status_code == 422


async def test_the_database_requires_a_course(db: Engine, load: Loader) -> None:
    await load([CURRY])
    with db.connect() as conn, pytest.raises(IntegrityError):
        conn.execute(text("UPDATE recipes SET course = NULL"))


async def test_browsing_without_a_query_lists_by_title(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA, CURRY])
    await create_household(client, fake_issuer, "ana")
    response = await get(client, fake_issuer, "/recipes")
    assert [r["title"] for r in response.json()] == [
        "Chicken and chickpea curry",
        "Quick tomato pasta",
    ]
    assert all(r["score"] is None for r in response.json())


async def test_cuisines_lists_what_the_library_has_most_common_first(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    risotto = seed("risotto", "Mushroom risotto", 40, "italian", ["300 g arborio rice"])
    await load([PASTA, CURRY, risotto])
    await create_household(client, fake_issuer, "ana")
    response = await get(client, fake_issuer, "/recipes/cuisines")
    assert response.status_code == 200
    assert response.json() == ["italian", "indian"]


async def test_browsing_pages_through_with_offset(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA, CURRY, STIR_FRY])
    await create_household(client, fake_issuer, "ana")
    first = await get(client, fake_issuer, "/recipes", limit=2)
    rest = await get(client, fake_issuer, "/recipes", limit=2, offset=2)
    assert [r["title"] for r in first.json()] == [
        "Beef and broccoli stir-fry",
        "Chicken and chickpea curry",
    ]
    assert [r["title"] for r in rest.json()] == ["Quick tomato pasta"]


async def test_reads_one_recipe_with_its_understood_ingredients(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA])
    await create_household(client, fake_issuer, "ana")
    [summary] = (await get(client, fake_issuer, "/recipes")).json()

    response = await get(client, fake_issuer, f"/recipes/{summary['id']}")
    assert response.status_code == 200
    recipe = response.json()
    assert recipe["method"] == ["Cook it."]
    assert recipe["licence"] == "Sweep original"
    garlic = recipe["ingredients"][2]
    assert garlic["ingredient"]["name"] == "garlic"
    assert (garlic["quantity"], garlic["unit"], garlic["base_quantity"]) == ("2", "clove", None)


async def test_imported_recipes_are_private_to_their_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([PASTA])
    mine = await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "ben", name="Ben's")
    recipe_id = uuid.uuid4()
    with db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (id, kind, household_id, title, summary, course, servings,"
                " licence, attribution, created_at)"
                " VALUES (:id, 'imported', :hh, 'Nonna''s lasagne', 'Family recipe', 'main', 6,"
                " 'unknown', 'nonna.example', now())"
            ),
            {"id": recipe_id, "hh": mine["household"]["id"]},
        )

    ben = fake_issuer.headers("ben")
    assert [r["title"] for r in (await client.get("/recipes", headers=ben)).json()] == [
        "Quick tomato pasta"
    ]
    assert (await client.get(f"/recipes/{recipe_id}", headers=ben)).status_code == 404
    ana_titles = [r["title"] for r in (await get(client, fake_issuer, "/recipes")).json()]
    assert ana_titles == ["Nonna's lasagne", "Quick tomato pasta"]


async def test_a_seed_recipe_cannot_belong_to_a_household(db: Engine) -> None:
    household_id = uuid.uuid4()
    with db.begin() as conn:
        conn.execute(
            text("INSERT INTO households (id, name, created_at) VALUES (:id, 'x', now())"),
            {"id": household_id},
        )
    with pytest.raises(IntegrityError), db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (id, kind, household_id, title, summary, servings,"
                " licence, attribution) VALUES (:id, 'seed', :hh, 't', 's', 1, 'l', 'a')"
            ),
            {"hh": household_id, "id": uuid.uuid4()},
        )


async def test_search_without_an_embedder_says_unavailable(
    database_url: str, db: Engine, fake_issuer: FakeIssuer
) -> None:
    app = create_app(
        Settings(database_url=database_url, voyage_api_key=None),
        token_verifier=fake_issuer.verifier(),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        await create_household(http, fake_issuer, "ana")
        response = await http.get(
            "/recipes", params={"q": "curry"}, headers=fake_issuer.headers("ana")
        )
        assert response.status_code == 503
        assert response.json()["code"] == "unavailable"
        # Browsing doesn't need the embedder, so it keeps working.
        assert (await http.get("/recipes", headers=fake_issuer.headers("ana"))).status_code == 200
    await app.state.engine.dispose()


async def test_recipes_need_a_signed_in_member(client: httpx.AsyncClient) -> None:
    assert (await client.get("/recipes")).status_code == 401
