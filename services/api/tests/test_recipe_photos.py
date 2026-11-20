"""A Member's own photo on their Imported Recipes (ADR 0031): cleaned, private, deleted
with what owns it."""

import io
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest
from PIL import Image

from app.errors import InvalidInput
from app.services import recipe_photos
from tests.conftest import FakeIssuer, Loader
from tests.helpers import create_household, idem
from tests.test_recipes import PASTA

pytestmark = pytest.mark.anyio


def jpeg(width: int = 1200, height: int = 900, *, upside_down: bool = False) -> bytes:
    """Red on top, blue below; camera details and, if asked, "rotate 180°" in EXIF."""
    image = Image.new("RGB", (width, height), "blue")
    image.paste("red", (0, 0, width, height // 2))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"  # Make
    if upside_down:
        exif[0x0112] = 3  # Orientation: rotate 180°
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    return out.getvalue()


def test_a_photo_is_cleaned_into_two_webp_sizes_without_its_metadata() -> None:
    files = recipe_photos.clean(jpeg(upside_down=True))
    assert set(files) == {"hero", "thumb"}
    for size, width in (("hero", 960), ("thumb", 360)):
        image = Image.open(io.BytesIO(files[size]))
        assert (image.format, image.size) == ("WEBP", (width, width * 3 // 4))
        assert not image.getexif() and "exif" not in image.info
    hero = Image.open(io.BytesIO(files["hero"])).convert("RGB")
    red, _, blue = hero.getpixel((480, 20))  # type: ignore[misc]
    assert blue > red  # turned upright: the camera's "upside down" was applied


@pytest.mark.parametrize("data", [b"not an image", b"\xff\xd8\xff" + b"0" * 50])
def test_something_that_isnt_a_readable_photo_is_refused(data: bytes) -> None:
    with pytest.raises(InvalidInput):
        recipe_photos.clean(data)


def test_a_signed_link_works_until_it_expires_and_only_as_signed() -> None:
    path = "h/r/p/thumb"
    expires, sig = recipe_photos.sign(path, now=1_000_000)
    assert recipe_photos.valid(path, expires, sig, now=1_000_000)
    assert expires - 1_000_000 >= 3600  # at least an hour
    assert not recipe_photos.valid(path, expires, sig, now=expires + 1)
    assert not recipe_photos.valid("h/r/OTHER/thumb", expires, sig, now=1_000_000)
    assert not recipe_photos.valid(path, expires + 1, sig, now=1_000_000)
    # The same link for an hour, so the phone's image cache keeps working.
    assert recipe_photos.sign(path, now=1_000_000 + 60) == (expires, sig)


LINES = [{"raw_text": "500 g beef mince"}]


async def save_recipe(client: httpx.AsyncClient, issuer: FakeIssuer, who: str) -> dict[str, Any]:
    response = await client.post(
        "/recipes/imported",
        json={"title": "Mum's lasagne", "servings": 4, "course": "main", "lines": LINES},
        headers=issuer.headers(who) | idem(),
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def put_photo(
    client: httpx.AsyncClient, issuer: FakeIssuer, who: str, recipe_id: str, data: bytes
) -> httpx.Response:
    return await client.put(
        f"/recipes/imported/{recipe_id}/photo",
        files={"photo": ("dish.jpg", data, "image/jpeg")},
        headers=issuer.headers(who) | idem(),
    )


Files = Callable[[], list[str]]


@pytest.fixture
def stored(photo_dir: Any) -> Files:
    return lambda: sorted(str(p.relative_to(photo_dir)) for p in photo_dir.rglob("*.webp"))


async def test_a_member_adds_sees_replaces_and_removes_their_photo(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, stored: Files
) -> None:
    await create_household(client, fake_issuer, "ana")
    recipe = await save_recipe(client, fake_issuer, "ana")
    assert recipe["image"] is None  # the app shows the food icon

    added = await put_photo(client, fake_issuer, "ana", recipe["id"], jpeg())
    assert added.status_code == 200, added.text
    image = added.json()["image"]
    assert image["author"] is None and image["source"] is None  # no credit line
    # Signed links, no sign-in needed: they work in a plain <img>.
    photo = await client.get(image["thumb_url"])
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/webp"
    assert "private" in photo.headers["cache-control"]
    page = await client.get(f"/recipes/{recipe['id']}", headers=fake_issuer.headers("ana"))
    assert page.json()["image"]["hero_url"].endswith(urlsplit(image["hero_url"]).query)
    assert len(stored()) == 2

    replaced = await put_photo(client, fake_issuer, "ana", recipe["id"], jpeg(800, 800))
    assert replaced.status_code == 200
    assert len(stored()) == 2  # the old files went
    assert (await client.get(image["thumb_url"])).status_code == 404

    removed = await client.delete(
        f"/recipes/imported/{recipe['id']}/photo", headers=fake_issuer.headers("ana") | idem()
    )
    assert removed.status_code == 200
    assert removed.json()["image"] is None
    assert stored() == []


async def test_a_tampered_or_unsigned_link_is_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer
) -> None:
    await create_household(client, fake_issuer, "ana")
    recipe = await save_recipe(client, fake_issuer, "ana")
    url = (await put_photo(client, fake_issuer, "ana", recipe["id"], jpeg())).json()["image"][
        "hero_url"
    ]
    path = urlsplit(url).path
    assert (await client.get(path)).status_code == 404
    assert (await client.get(url.replace("sig=", "sig=0"))).status_code == 404
    assert (await client.get(url.replace("/hero", "/thumb"))).status_code == 404


async def test_only_your_households_own_recipes_take_a_photo(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, load: Loader
) -> None:
    await load([PASTA])
    await create_household(client, fake_issuer, "ana")
    await create_household(client, fake_issuer, "ben")
    recipe = await save_recipe(client, fake_issuer, "ana")
    assert (await put_photo(client, fake_issuer, "ben", recipe["id"], jpeg())).status_code == 404
    listed = (await client.get("/recipes", headers=fake_issuer.headers("ana"))).json()
    seed = next(r for r in listed if r["kind"] == "seed")
    assert (await put_photo(client, fake_issuer, "ana", seed["id"], jpeg())).status_code == 404


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"GIF89a" + b"0" * 100, "JPEG, PNG or WebP"),
        (b"\xff\xd8\xff" + b"0" * 5_000_000, "5 MB"),
    ],
)
async def test_the_wrong_kind_or_size_of_file_is_refused(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, data: bytes, message: str
) -> None:
    await create_household(client, fake_issuer, "ana")
    recipe = await save_recipe(client, fake_issuer, "ana")
    refused = await put_photo(client, fake_issuer, "ana", recipe["id"], data)
    assert refused.status_code == 422
    assert message in refused.json()["detail"]


async def test_deleting_the_recipe_or_the_last_member_deletes_the_photos(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, stored: Files
) -> None:
    await create_household(client, fake_issuer, "ana")
    first = await save_recipe(client, fake_issuer, "ana")
    second = await save_recipe(client, fake_issuer, "ana")
    for recipe in (first, second):
        await put_photo(client, fake_issuer, "ana", recipe["id"], jpeg())
    assert len(stored()) == 4

    gone = await client.delete(
        f"/recipes/imported/{first['id']}", headers=fake_issuer.headers("ana") | idem()
    )
    assert gone.status_code == 204
    assert len(stored()) == 2

    left = await client.delete("/me", headers=fake_issuer.headers("ana"))
    assert left.status_code == 204, left.text
    assert stored() == []
