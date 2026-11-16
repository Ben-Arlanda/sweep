"""Dietary Rules (hard, enforced by code) and Preferences (soft, for the agent to weigh)."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, text

from app.data.diet import CHECK_LABEL, CONTAINS, Diet
from app.data.ingredients import INGREDIENTS
from app.models import Ingredient, Recipe, RecipeIngredient
from app.services.diet import DietaryRules, check_recipe
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem, invite, join
from tests.test_recipes import CURRY, PASTA, STIR_FRY, seed

pytestmark = pytest.mark.anyio

RULES = "/households/current/dietary-rules"
PREFS = "/households/current/preferences"


# --- The reference data ---------------------------------------------------------------


def test_every_flagged_name_is_a_real_ingredient() -> None:
    known = {i.name for i in INGREDIENTS}
    assert set(CONTAINS) - known == set()
    assert set(CHECK_LABEL) - known == set()


def test_squid_is_seafood() -> None:
    # Added with the link-import starters (2026-11-16). A starter with no flags counts
    # as fine for every diet, so a new animal food must be flagged when it's added.
    assert "seafood" in CONTAINS["squid"]


def test_eggs_are_not_dairy() -> None:
    # They sit in the dairy aisle, which is exactly how this mistake gets made.
    assert "dairy" not in CONTAINS["eggs"]


# --- Checking one recipe (pure code, no database) -----------------------------------


def recipe(*lines: tuple[str | None, str]) -> Recipe:
    """A recipe in memory. Each line is (Ingredient name or None if unmatched, raw text)."""
    return Recipe(
        title="Test",
        ingredients=[
            RecipeIngredient(
                position=n,
                raw_text=raw,
                ingredient=Ingredient(id=uuid.uuid4(), name=name) if name else None,
                needs_review=name is None,
                optional=False,
            )
            for n, (name, raw) in enumerate(lines)
        ],
    )


def rules(*diets: Diet, excluded: frozenset[uuid.UUID] = frozenset()) -> DietaryRules:
    return DietaryRules(frozenset(diets), excluded)


def test_a_recipe_with_chicken_breaks_vegetarian() -> None:
    check = check_recipe(recipe(("chicken thigh", "500 g chicken thigh")), rules(Diet.VEGETARIAN))
    assert check.breaks == ["chicken thigh (vegetarian)"]


def test_hidden_gluten_and_dairy_are_caught() -> None:
    dish = recipe(("soy sauce", "2 tbsp soy sauce"), ("butter", "20 g butter"))
    check = check_recipe(dish, rules(Diet.GLUTEN_FREE, Diet.DAIRY_FREE))
    assert check.breaks == ["soy sauce (gluten free)", "butter (dairy free)"]


def test_brand_dependent_ingredients_pass_with_a_label_warning() -> None:
    check = check_recipe(recipe(("stock cubes", "2 stock cubes")), rules(Diet.GLUTEN_FREE))
    assert check.breaks == []
    assert check.check_label == ["stock cubes (gluten free)"]


def test_an_unmatched_line_is_unknown_so_the_recipe_fails_safe() -> None:
    check = check_recipe(recipe((None, "1 jar mystery sauce")), rules(Diet.VEGAN))
    assert check.breaks == ["1 jar mystery sauce (couldn't check)"]


def test_unmatched_lines_dont_matter_without_rules() -> None:
    assert check_recipe(recipe((None, "1 jar mystery sauce")), rules()).breaks == []


def test_an_excluded_ingredient_breaks_the_rule() -> None:
    dish = recipe(("mushrooms", "200 g mushrooms"))
    mushrooms = dish.ingredients[0].ingredient
    assert mushrooms is not None
    check = check_recipe(dish, rules(excluded=frozenset({mushrooms.id})))
    assert check.breaks == ["mushrooms (excluded)"]


def with_household_ingredient(name: str) -> Recipe:
    """A recipe with one line linked to a Household Ingredient: one a Member made, so
    Sweep has no idea what's in it."""
    satay = Ingredient(id=uuid.uuid4(), name=name, household_id=uuid.uuid4())
    line = RecipeIngredient(
        position=0, raw_text=f"3 tbsp {name}", ingredient=satay, needs_review=False, optional=False
    )
    return Recipe(title="Test", ingredients=[line])


def test_a_household_ingredient_cant_be_checked_so_the_recipe_fails_closed() -> None:
    check = check_recipe(with_household_ingredient("satay sauce"), rules(Diet.VEGETARIAN))
    assert check.breaks == ["satay sauce (couldn't check)"]


def test_household_ingredients_dont_matter_without_rules() -> None:
    assert check_recipe(with_household_ingredient("satay sauce"), rules()).breaks == []


def test_an_excluded_household_ingredient_says_excluded() -> None:
    dish = with_household_ingredient("satay sauce")
    satay = dish.ingredients[0].ingredient
    assert satay is not None
    assert check_recipe(dish, rules(excluded=frozenset({satay.id}))).breaks == [
        "satay sauce (excluded)"
    ]


def test_vegan_excludes_eggs_and_honey_but_vegetarian_allows_them() -> None:
    dish = recipe(("eggs", "2 eggs"), ("honey", "1 tbsp honey"))
    assert check_recipe(dish, rules(Diet.VEGETARIAN)).breaks == []
    assert check_recipe(dish, rules(Diet.VEGAN)).breaks == ["eggs (vegan)", "honey (vegan)"]


# --- The API ------------------------------------------------------------------------


async def ingredient_id(db: Engine, name: str) -> str:
    with db.connect() as conn:
        found = conn.execute(text("SELECT id FROM ingredients WHERE name = :n"), {"n": name})
        return str(found.scalar_one())


async def put(
    client: httpx.AsyncClient, issuer: FakeIssuer, path: str, body: dict[str, Any], who: str = "ana"
) -> httpx.Response:
    return await client.put(path, json=body, headers={**issuer.headers(who), **idem()})


async def test_a_new_household_has_no_rules_and_no_preferences(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    got = await client.get(RULES, headers=fake_issuer.headers("ana"))
    assert got.json() == {"diets": [], "excluded_ingredients": []}
    got = await client.get(PREFS, headers=fake_issuer.headers("ana"))
    assert got.json() == {"household_size": None, "cuisines": [], "plan_weekdays": [1, 2, 3, 4, 5]}


async def test_any_member_can_set_rules_and_the_whole_household_sees_them(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, db: Engine
) -> None:
    # Not Owner-only: the Member with the allergy is the one who'll set it.
    await create_household(client, fake_issuer, "ana")
    await join(client, fake_issuer, "ben", await invite(client, fake_issuer, "ana"))
    mushrooms = await ingredient_id(db, "mushrooms")

    body = {"diets": ["gluten_free", "vegetarian"], "excluded_ingredient_ids": [mushrooms]}
    response = await put(client, fake_issuer, RULES, body, who="ben")
    assert response.status_code == 200, response.text

    got = (await client.get(RULES, headers=fake_issuer.headers("ana"))).json()
    assert got["diets"] == ["gluten_free", "vegetarian"]  # sorted, so the order is stable
    assert [i["name"] for i in got["excluded_ingredients"]] == ["mushrooms"]


async def test_rules_are_private_to_the_household(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "cat")
    await put(client, fake_issuer, RULES, {"diets": ["vegan"], "excluded_ingredient_ids": []})
    got = await client.get(RULES, headers=fake_issuer.headers("cat"))
    assert got.json()["diets"] == []


async def test_unknown_diets_and_ingredients_are_rejected(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    bad_diet = await put(client, fake_issuer, RULES, {"diets": ["keto"]})
    assert bad_diet.status_code == 422
    bad_id = {"diets": [], "excluded_ingredient_ids": [str(uuid.uuid4())]}
    assert (await put(client, fake_issuer, RULES, bad_id)).status_code == 404


async def test_preferences_round_trip_and_are_validated(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    # weekly_budget was removed (ADR 0010); an older app still sending it is ignored.
    body = {"household_size": 2, "cuisines": ["Italian", "greek"], "weekly_budget": "120.00"}
    assert (await put(client, fake_issuer, PREFS, body)).status_code == 200
    got = (await client.get(PREFS, headers=fake_issuer.headers("ana"))).json()
    assert got == {
        "household_size": 2,
        "cuisines": ["greek", "italian"],
        "plan_weekdays": [1, 2, 3, 4, 5],
    }

    for bad in ({"household_size": 0}, {"cuisines": ["x" * 50]}):
        assert (await put(client, fake_issuer, PREFS, bad)).status_code == 422, bad


# --- Rules filter the Recipe Knowledge Base -----------------------------------------

SALAD = seed(
    "chickpea-salad",
    "Chickpea salad",
    15,
    "middle-eastern",
    ["400 g can chickpeas", "1 cucumber", "2 tomatoes", "2 tbsp olive oil"],
)


async def titles(client: httpx.AsyncClient, issuer: FakeIssuer, **params: Any) -> list[str]:
    response = await client.get("/recipes", params=params, headers=issuer.headers("ana"))
    assert response.status_code == 200, response.text
    return sorted(r["title"] for r in response.json())


async def test_rules_filter_browsing_and_search(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([CURRY, PASTA, STIR_FRY, SALAD])
    await create_household(client, fake_issuer, "ana")
    assert len(await titles(client, fake_issuer)) == 4

    await put(client, fake_issuer, RULES, {"diets": ["vegetarian"]})
    # Pasta has parmesan (fine for vegetarian); curry and stir-fry have meat.
    assert await titles(client, fake_issuer) == ["Chickpea salad", "Quick tomato pasta"]

    await put(client, fake_issuer, RULES, {"diets": ["vegetarian", "gluten_free"]})
    assert await titles(client, fake_issuer, q="something light") == ["Chickpea salad"]

    await put(client, fake_issuer, RULES, {"diets": ["dairy_free"]})
    assert "Quick tomato pasta" not in await titles(client, fake_issuer)


async def test_a_recipe_with_an_unmatched_line_is_hidden_when_rules_are_set(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    mystery = seed("mystery", "Mystery stew", 30, "british", ["1 jar zorblax relish", "1 onion"])
    await load([mystery, SALAD])
    await create_household(client, fake_issuer, "ana")
    assert "Mystery stew" in await titles(client, fake_issuer)
    await put(client, fake_issuer, RULES, {"diets": ["vegan"]})
    assert await titles(client, fake_issuer) == ["Chickpea salad"]


def insert_imported(db: Engine, household_id: str, title: str, lines: list[str | None]) -> None:
    """An Imported Recipe straight into the database (4d's import routes come next).
    Each line is an Ingredient id, or None for a line nothing matched."""
    recipe_id = uuid.uuid4()
    with db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (id, kind, household_id, title, summary, course, servings,"
                " licence, attribution, created_at)"
                " VALUES (:id, 'imported', :hh, :title, '', 'main', 4, 'private', 'Home', now())"
            ),
            {"id": recipe_id, "hh": household_id, "title": title},
        )
        for n, ingredient in enumerate(lines):
            conn.execute(
                text(
                    "INSERT INTO recipe_ingredients (id, recipe_id, position, raw_text,"
                    " ingredient_id, optional, parse_method, needs_review)"
                    " VALUES (:id, :r, :n, :raw, :i, false, 'rule', :review)"
                ),
                {
                    "id": uuid.uuid4(),
                    "r": recipe_id,
                    "n": n,
                    "raw": f"line {n}",
                    "i": ingredient,
                    "review": ingredient is None,
                },
            )


async def make_satay_household(client: httpx.AsyncClient, issuer: FakeIssuer, db: Engine) -> None:
    """Ana's Household, with two Imported Recipes: one uses a Household Ingredient
    (satay sauce), one uses only starters (onion)."""
    home = await create_household(client, issuer, "ana")
    made = await client.post(
        "/ingredients", json={"name": "satay sauce"}, headers=issuer.headers("ana") | idem()
    )
    assert made.status_code == 200, made.text
    hh = home["household"]["id"]
    insert_imported(db, hh, "Satay noodles", [made.json()["id"]])
    insert_imported(db, hh, "Onion soup", [await ingredient_id(db, "onion")])


async def test_a_household_ingredient_hides_the_recipe_once_rules_are_set(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([SALAD])
    await make_satay_household(client, fake_issuer, db)
    assert await titles(client, fake_issuer) == ["Chickpea salad", "Onion soup", "Satay noodles"]

    await put(client, fake_issuer, RULES, {"diets": ["vegetarian"]})
    # Search runs through the same filter (_filtered); these rows have no embeddings.
    assert await titles(client, fake_issuer) == ["Chickpea salad", "Onion soup"]


async def test_your_recipes_lists_every_imported_recipe_with_why_its_hidden(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader, db: Engine
) -> None:
    await load([SALAD])
    await make_satay_household(client, fake_issuer, db)
    await put(client, fake_issuer, RULES, {"diets": ["vegetarian"]})

    response = await client.get("/recipes/imported", headers=fake_issuer.headers("ana"))
    assert response.status_code == 200, response.text
    found = {r["title"]: r["rule_breaks"] for r in response.json()}
    # Seed Recipes aren't "yours"; hidden ones are still listed, with the reason.
    assert found == {"Satay noodles": ["satay sauce (couldn't check)"], "Onion soup": []}

    # Another Household sees none of them.
    await create_household(client, fake_issuer, "ben", name="Ben's")
    other = await client.get("/recipes/imported", headers=fake_issuer.headers("ben"))
    assert other.json() == []


def test_parmesan_needs_a_label_check_for_vegetarians() -> None:
    # Found in a live agent run: traditional parmesan uses animal rennet.
    check = check_recipe(recipe(("parmesan", "50 g parmesan")), rules(Diet.VEGETARIAN))
    assert check.breaks == []
    assert check.check_label == ["parmesan (vegetarian)"]
