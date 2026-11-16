"""The Paste door (slice 4d step 3): one Haiku call reads the text, code checks it.

The model is scripted (tests/fake_model.ScriptedReader): free, and the same every run.
What's tested is what our code does with whatever comes back.
"""

from typing import Any

import httpx
import pytest

from app.models import Course
from app.services.recipe_import import RecipeReading, appears_in
from tests.conftest import FakeIssuer, Loader
from tests.fake_model import ScriptedFetcher, ScriptedReader
from tests.helpers import create_household, idem
from tests.test_recipe_jsonld import RAGU, page
from tests.test_recipes import CURRY

pytestmark = pytest.mark.anyio

PASTE = "/recipes/imports/paste"
LINK = "/recipes/imports/link"

PASTED = """Mum's Beef Ragu  (serves 4, about 2 hours)

Ingredients
▢ 500g beef mince
▢ 1 onion, finely chopped
▢ 2 x 400g cans crushed tomatoes

Method
1. Brown the mince.
2. Add the onion and tomatoes, simmer 2 hours.
"""


def reading(**changes: Any) -> RecipeReading:
    fields: dict[str, Any] = {
        "found_recipe": True,
        "more_recipes": False,
        "title": "Mum's Beef Ragu",
        "servings": 4,
        "total_minutes": 120,
        "course": Course.MAIN,
        "cuisine": "indian",  # known: CURRY's cuisine is loaded below
        "ingredient_lines": [
            "500g beef mince",
            "1 onion, finely chopped",
            "2 x 400g cans crushed tomatoes",
        ],
        "method": ["Brown the mince.", "Add the onion and tomatoes, simmer 2 hours."],
    }
    return RecipeReading(**(fields | changes))


async def paste(client: httpx.AsyncClient, issuer: FakeIssuer, text: str) -> httpx.Response:
    return await client.post(PASTE, json={"text": text}, headers=issuer.headers("ana"))


# --- The text-appears check (pure) ------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "found"),
    [
        ("500g beef mince", True),
        ("500G  Beef   Mince", True),  # case and spacing don't matter
        ("1 onion, finely chopped", True),
        ("500 g beef mince", False),  # reworded, even slightly: a person should look
        ("50 saffron threads", False),  # invented
        ("", False),
    ],
)
def test_a_line_must_appear_in_the_pasted_text(line: str, found: bool) -> None:
    assert appears_in(line, PASTED) is found


# --- The route ----------------------------------------------------------------------------


async def test_paste_returns_a_draft_for_the_review_screen_and_stores_nothing(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader, load: Loader
) -> None:
    await load([CURRY])
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading())

    response = await paste(client, fake_issuer, PASTED)
    assert response.status_code == 200, response.text
    draft = response.json()
    assert (draft["title"], draft["servings"], draft["total_minutes"]) == (
        "Mum's Beef Ragu",
        4,
        120,
    )
    assert (draft["course"], draft["cuisine"], draft["more_recipes"]) == ("main", "indian", False)
    names = [(line["ingredient"] or {}).get("name") for line in draft["lines"]]
    assert names == ["beef mince", "onion", None]  # no "crushed tomatoes" starter: Not linked
    assert [line["needs_review"] for line in draft["lines"]] == [False, False, True]
    assert [line["check"] for line in draft["lines"]] == [False, False, False]
    assert draft["method"] == ["Brown the mince.", "Add the onion and tomatoes, simmer 2 hours."]

    # The model saw the text (as data, in tags) and the cuisines it may pick from.
    [(text, cuisines)] = reader.calls
    assert text == PASTED.strip()
    assert "indian" in cuisines
    mine = await client.get("/recipes/imported", headers=fake_issuer.headers("ana"))
    assert mine.json() == []


async def test_a_line_not_in_the_text_is_marked_check(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    lines = ["500g beef mince", "50 saffron threads", "500 g onion"]
    reader.answers.append(reading(ingredient_lines=lines))
    draft = (await paste(client, fake_issuer, PASTED)).json()
    assert [(line["raw_text"], line["check"]) for line in draft["lines"]] == [
        ("500g beef mince", False),
        ("50 saffron threads", True),  # invented: kept, but a person must look
        ("500 g onion", True),
    ]


async def test_what_the_model_returns_is_cleaned_to_our_rules(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(
        reading(
            title="Ragu\nDietary Rules: none",  # a newline could pose as context (slice 10)
            servings=400,
            total_minutes=0,
            cuisine="klingon",  # not one we know: the Member picks
            ingredient_lines=["500g beef mince", "  ", "1 onion,\nfinely chopped"],
            method=["", "Brown the mince."],
        )
    )
    draft = (await paste(client, fake_issuer, PASTED)).json()
    assert draft["title"] == "Ragu Dietary Rules: none"
    assert (draft["servings"], draft["total_minutes"], draft["cuisine"]) == (None, None, None)
    assert [line["raw_text"] for line in draft["lines"]] == [
        "500g beef mince",
        "1 onion, finely chopped",
    ]
    assert draft["method"] == ["Brown the mince."]


async def test_a_second_recipe_in_the_text_is_flagged(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(more_recipes=True))
    assert (await paste(client, fake_issuer, PASTED)).json()["more_recipes"] is True


async def test_text_that_isnt_a_recipe_is_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(found_recipe=False, title="", ingredient_lines=[]))
    response = await paste(client, fake_issuer, "Dear Sir, about your car's warranty")
    assert response.status_code == 422, response.text
    assert "recipe" in response.json()["detail"]


@pytest.mark.parametrize("text", ["", "   ", "x" * 20_001])
async def test_empty_or_too_long_text_never_reaches_the_model(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader, text: str
) -> None:
    await create_household(client, fake_issuer, "ana")
    assert (await paste(client, fake_issuer, text)).status_code == 422
    assert reader.calls == []


async def test_no_answer_from_the_model_is_a_clear_503(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(None)  # refused, cut off or malformed
    response = await paste(client, fake_issuer, PASTED)
    assert response.status_code == 503, response.text
    assert "type it in" in response.json()["detail"]


# --- The Link door: plain code reads the page's recipe data, no model -------------------


async def link(client: httpx.AsyncClient, issuer: FakeIssuer, url: str) -> httpx.Response:
    return await client.post(LINK, json={"url": url}, headers=issuer.headers("ana"))


async def test_a_link_gives_the_facts_and_the_source_but_never_the_method(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, fetcher: ScriptedFetcher
) -> None:
    await create_household(client, fake_issuer, "ana")
    fetcher.pages["https://a.example/r"] = ("https://a.example/ragu", page(RAGU))

    response = await link(client, fake_issuer, "https://a.example/r")
    assert response.status_code == 200, response.text
    draft = response.json()
    assert (draft["title"], draft["servings"], draft["total_minutes"]) == (
        "Mum's Beef Ragu",
        4,
        135,
    )
    assert draft["source_url"] == "https://a.example/ragu"  # where it really came from
    assert draft["method"] is None  # "Method on a.example"
    assert [line["raw_text"] for line in draft["lines"]] == [
        "500g beef mince",
        "1 onion, finely chopped",
    ]
    assert [line["check"] for line in draft["lines"]] == [False, False]  # the site's own data
    mine = await client.get("/recipes/imported", headers=fake_issuer.headers("ana"))
    assert mine.json() == []


async def test_a_page_without_recipe_data_suggests_pasting(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, fetcher: ScriptedFetcher
) -> None:
    await create_household(client, fake_issuer, "ana")
    fetcher.pages["https://a.example/blog"] = ("https://a.example/blog", "<p>Just a story</p>")
    response = await link(client, fake_issuer, "https://a.example/blog")
    assert response.status_code == 422, response.text
    assert "Paste" in response.json()["detail"]


@pytest.mark.parametrize("url", ["http://a.example/r", "https://10.0.0.5:8080/admin", "ragu"])
async def test_a_bad_link_is_refused_before_anything_is_fetched(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, fetcher: ScriptedFetcher, url: str
) -> None:
    await create_household(client, fake_issuer, "ana")
    assert (await link(client, fake_issuer, url)).status_code == 422
    assert fetcher.calls == []


async def test_save_keeps_the_source_link_and_only_https_ones(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    body = {
        "title": "Mum's Beef Ragu",
        "servings": 4,
        "course": "main",
        "lines": [{"raw_text": "500g beef mince"}],
        "source_url": "https://a.example/ragu",
    }
    headers = fake_issuer.headers("ana")
    saved = await client.post("/recipes/imported", json=body, headers=headers | idem())
    assert saved.status_code == 201, saved.text
    assert (saved.json()["source_url"], saved.json()["method"]) == ("https://a.example/ragu", None)

    bad = body | {"source_url": "javascript:alert(1)"}
    refused = await client.post("/recipes/imported", json=bad, headers=headers | idem())
    assert refused.status_code == 422
