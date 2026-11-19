"""R2 keyword search and R3 rank fusion (slice 9). R1 lives in test_recipes.py."""

import uuid

import httpx
import pytest
from sqlalchemy import Engine, text

from app.db import make_engine, make_sessionmaker
from app.models import Course
from app.services import recipes
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem
from tests.test_imported_recipes import IMPORTED, nonna, save
from tests.test_recipes import CURRY, PASTA, PAVLOVA, STIR_FRY, seed

pytestmark = pytest.mark.anyio

PRAWN_PASTA = seed(
    "garlic-prawn-pasta",
    "Garlic linguine",  # "prawn" is only in the lines
    20,
    "italian",
    ["400 g pasta", "300 g prawns", "3 cloves garlic", "1 lemon"],
)
CURRIES = [CURRY, PASTA, PAVLOVA, STIR_FRY, PRAWN_PASTA]


async def titles(
    database_url: str,
    query: str,
    filters: recipes.RecipeFilters | None = None,
    household_id: uuid.UUID | None = None,
) -> list[str]:
    engine = make_engine(database_url)
    async with make_sessionmaker(engine)() as session:
        found = await recipes.keyword_search(
            session,
            household_id or uuid.uuid4(),
            query,
            filters or recipes.RecipeFilters(),
            limit=10,
        )
    await engine.dispose()
    return [r.title for r, _score in found]


async def test_a_title_word_outranks_the_same_word_in_the_lines(
    database_url: str, load: Loader
) -> None:
    await load(CURRIES)
    # Both have pasta; only the tomato one says so in its title.
    assert (await titles(database_url, "pasta"))[:2] == ["Quick tomato pasta", "Garlic linguine"]


async def test_any_word_can_match_not_only_all_of_them(database_url: str, load: Loader) -> None:
    await load(CURRIES)
    # websearch_to_tsquery would need every word; "cosy" and "dinner" are in no recipe.
    assert await titles(database_url, "cosy chicken dinner") == ["Chicken and chickpea curry"]


async def test_ingredient_aliases_and_word_endings_match(database_url: str, load: Loader) -> None:
    await load(CURRIES)
    assert await titles(database_url, "shrimp") == ["Garlic linguine"]  # alias of prawns
    assert await titles(database_url, "garbanzo") == ["Chicken and chickpea curry"]
    assert await titles(database_url, "curries") == ["Chicken and chickpea curry"]  # stemmed


async def test_filters_are_hard_limits(database_url: str, load: Loader) -> None:
    await load(CURRIES)
    quick = recipes.RecipeFilters(max_minutes=30)
    assert await titles(database_url, "chicken curry", quick) == []
    desserts = recipes.RecipeFilters(course=Course.DESSERT)
    assert await titles(database_url, "pavlova pasta", desserts) == ["Pavlova"]


async def test_no_useful_words_finds_nothing_without_an_error(
    database_url: str, load: Loader
) -> None:
    await load(CURRIES)
    assert await titles(database_url, "the and of") == []  # stop words only
    assert await titles(database_url, "!!! & | :*") == []  # tsquery syntax is just text
    assert await titles(database_url, "") == []


async def test_imported_recipes_are_searchable_after_save_and_edit_and_stay_private(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, database_url: str, db: Engine
) -> None:
    await create_household(client, fake_issuer, "ana")
    recipe = (await save(client, fake_issuer, nonna())).json()
    with db.connect() as conn:
        hid = conn.execute(
            text("SELECT household_id FROM recipes WHERE id = :id"), {"id": recipe["id"]}
        ).scalar_one()
    assert await titles(database_url, "lasagne", household_id=hid) == ["Nonna's lasagne"]
    assert await titles(database_url, "lasagne") == []  # another Household

    edited = nonna(title="Zucchini bake", lines=[{"raw_text": "2 courgettes"}])
    response = await client.put(
        f"{IMPORTED}/{recipe['id']}", json=edited, headers=fake_issuer.headers("ana") | idem()
    )
    assert response.status_code == 200, response.text
    assert await titles(database_url, "lasagne", household_id=hid) == []
    assert await titles(database_url, "zucchini", household_id=hid) == ["Zucchini bake"]


def test_rank_fusion_rewards_being_high_in_either_list() -> None:
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    fused = recipes.fuse([[a, b, c], [c, d]], k=60)
    # c: 1/63 + 1/61 beats a: 1/61 alone. b and d tie (1/62 each): earlier list first.
    assert [i for i, _score in fused] == [c, a, b, d]
    assert recipes.fuse([[], []]) == []
    assert [i for i, _ in recipes.fuse([[a, b]])] == [a, b]  # one list keeps its order


async def test_accents_dont_matter_either_way(database_url: str, load: Loader) -> None:
    brulee = seed("creme-brulee", "Crème brûlée", 60, "french", ["4 egg yolks", "300 ml cream"])
    helene = seed("pear-belle-helene", "Pear belle helene", 40, "french", ["4 pears"])
    await load([brulee, helene])
    assert await titles(database_url, "creme brulee") == ["Crème brûlée"]
    assert await titles(database_url, "hélène") == ["Pear belle helene"]
