"""An Imported Recipe's description: the intro a recipe opens with, copied, never written.

Shown under the title on the recipe screen (it's the recipe's `summary`). Pasted text
is checked like the lines: a description not in the text is dropped, so the model can't
write one. A Link keeps facts only (ADR 0020), so no description from a website.
"""

import httpx
import pytest

from tests.conftest import FakeIssuer
from tests.fake_model import ScriptedFetcher, ScriptedReader
from tests.helpers import create_household
from tests.test_imported_recipes import nonna, save
from tests.test_recipe_import import JPEG, LINK, PASTED, PHOTO, paste, reading
from tests.test_recipe_jsonld import RAGU, page

pytestmark = pytest.mark.anyio

INTRO = "My mum's Sunday ragu, slow and rich."
WITH_INTRO = PASTED.replace("\n\nIngredients", f"\n\n{INTRO}\n\nIngredients")


async def test_a_pasted_description_is_kept_when_its_in_the_text(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(summary="My mum's Sunday ragu,\nslow and rich."))

    draft = (await paste(client, fake_issuer, WITH_INTRO)).json()

    assert draft["summary"] == INTRO  # one paragraph


async def test_a_description_the_model_wrote_is_dropped(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(summary="A nut-free family favourite."))

    draft = (await paste(client, fake_issuer, WITH_INTRO)).json()

    assert draft["summary"] is None


async def test_a_photos_description_is_kept_for_a_person_to_read(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(summary=INTRO))

    response = await client.post(
        PHOTO,
        files=[("photos", ("p.jpg", JPEG, "image/jpeg"))],
        headers=fake_issuer.headers("ana"),
    )

    assert response.json()["summary"] == INTRO


async def test_no_description_is_none(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(summary=None))

    assert (await paste(client, fake_issuer, PASTED)).json()["summary"] is None


async def test_a_link_never_brings_a_description(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, fetcher: ScriptedFetcher
) -> None:
    await create_household(client, fake_issuer, "ana")
    described = RAGU | {"description": "The best ragu on the internet."}
    fetcher.pages["https://a.example/r"] = ("https://a.example/ragu", page(described))

    response = await client.post(
        LINK, json={"url": "https://a.example/r"}, headers=fake_issuer.headers("ana")
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"] is None


async def test_a_saved_description_shows_on_the_recipe_and_can_be_edited(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    saved = (await save(client, fake_issuer, nonna(summary=INTRO))).json()
    assert saved["summary"] == INTRO

    edited = await client.put(
        f"/recipes/imported/{saved['id']}",
        json=nonna(summary=None),
        headers=fake_issuer.headers("ana") | {"Idempotency-Key": "edit-1"},
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["summary"] == ""


@pytest.mark.parametrize("summary", ["x" * 501, "line one\nline two"])
async def test_a_description_is_one_paragraph_of_up_to_500_characters(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, summary: str
) -> None:
    await create_household(client, fake_issuer, "ana")

    response = await save(client, fake_issuer, nonna(summary=summary))

    assert response.status_code == 422
