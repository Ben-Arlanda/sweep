"""The plain-code rules for Recipe Images (slice 4f, ADR 0027). No network, no model."""

from typing import Any

import pytest

from app.services.recipe_image_check import ImageCheck, passes, title_clash
from scripts.recipe_images import (
    commons_candidate,
    crop_box,
    fits,
    licence_name,
    openverse_candidate,
    plain_text,
    queries,
)
from tests.test_recipes import PASTA


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("CC BY 2.0", "CC BY 2.0"),
        ("CC BY-SA 4.0", "CC BY-SA 4.0"),
        ("cc-by-sa-3.0", "CC BY-SA 3.0"),
        ("CC0", "CC0 1.0"),
        ("Public domain", "Public Domain"),
        ("CC BY-NC 2.0", None),  # Sweep is a product
        ("CC BY-NC-SA 2.0", None),
        ("CC BY-ND 4.0", None),  # we crop and resize
        ("GFDL", None),
        ("Attribution", None),  # not a licence we can name
        ("", None),
    ],
)
def test_only_open_licences_that_allow_products_and_changes(given: str, expected: str) -> None:
    assert licence_name(given) == expected


@pytest.mark.parametrize(
    ("size", "ok"),
    [
        ((2048, 1344), True),
        ((1016, 763), True),
        ((960, 720), True),  # exactly 4:3 at the hero width
        ((800, 600), False),  # too small for the hero
        ((1000, 700), False),  # a 4:3 crop would be 933 wide
        ((3000, 1000), False),  # a panorama: the crop loses most of it
        ((1200, 1600), False),  # portrait: the crop loses nearly half
    ],
)
def test_an_image_fits_when_a_4_by_3_crop_is_big_enough(size: tuple[int, int], ok: bool) -> None:
    assert fits(*size) is ok


def test_the_crop_is_4_by_3_from_the_middle() -> None:
    assert crop_box(2000, 1000) == (333, 0, 1666, 1000)
    assert crop_box(1200, 1200) == (0, 150, 1200, 1050)
    assert crop_box(1024, 768) == (0, 0, 1024, 768)


def test_html_credits_become_plain_text() -> None:
    assert plain_text('<a href="https://x">Joe  Mahoney</a>\n') == "Joe Mahoney"
    assert plain_text("Tom &amp; Jo") == "Tom & Jo"


def commons_page(**info: Any) -> dict[str, Any]:
    meta = {
        "LicenseShortName": {"value": "CC BY 2.0"},
        "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/2.0"},
        "Artist": {"value": '<a href="https://flickr.com/x">Joe Mahoney</a>'},
    }
    base = {
        "width": 2048,
        "height": 1344,
        "mime": "image/jpeg",
        "thumburl": "https://upload.wikimedia.org/thumb/960px-Shakshuka1.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Shakshuka1.jpg",
        "extmetadata": meta,
    }
    return {"title": "File:Shakshuka1.jpg", "imageinfo": [base | info]}


def test_a_commons_file_becomes_a_candidate_with_its_credit() -> None:
    found = commons_candidate(commons_page())
    assert found is not None
    assert found.source == "wikimedia"
    assert found.author == "Joe Mahoney"
    assert found.licence == "CC BY 2.0"
    assert found.licence_url == "https://creativecommons.org/licenses/by/2.0"
    assert found.source_url == "https://commons.wikimedia.org/wiki/File:Shakshuka1.jpg"
    assert found.download_url.endswith("960px-Shakshuka1.jpg")


def test_commons_files_that_break_a_rule_are_left_out() -> None:
    nc = {"LicenseShortName": {"value": "CC BY-NC 2.0"}, "Artist": {"value": "A"}}
    assert commons_candidate(commons_page(extmetadata=nc)) is None
    assert commons_candidate(commons_page(width=800, height=600)) is None
    assert commons_candidate(commons_page(mime="image/svg+xml")) is None
    no_author = {"LicenseShortName": {"value": "CC BY 2.0"}, "Artist": {"value": ""}}
    assert commons_candidate(commons_page(extmetadata=no_author)) is None  # BY needs a name


def test_public_domain_needs_no_author() -> None:
    pd = {"LicenseShortName": {"value": "Public domain"}}
    found = commons_candidate(commons_page(extmetadata=pd))
    assert found is not None and found.author == "Unknown"


def openverse_result(**fields: Any) -> dict[str, Any]:
    return {
        "id": "e781",
        "url": "https://live.staticflickr.com/5584/15305126182_fce224af50_b.jpg",
        "foreign_landing_url": "https://www.flickr.com/photos/34948727@N00/15305126182",
        "creator": "Alpha",
        "license": "by-sa",
        "license_version": "2.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/2.0/",
        "width": 1024,
        "height": 768,
        "source": "flickr",
        "filetype": "jpg",
    } | fields


def test_an_openverse_result_becomes_a_candidate() -> None:
    found = openverse_candidate(openverse_result())
    assert found is not None
    assert (found.source, found.licence, found.author) == ("openverse", "CC BY-SA 2.0", "Alpha")
    assert found.source_url.startswith("https://www.flickr.com/photos/")


def test_openverse_results_that_break_a_rule_are_left_out() -> None:
    assert openverse_candidate(openverse_result(license="by-nc")) is None
    assert openverse_candidate(openverse_result(width=640, height=480)) is None
    assert openverse_candidate(openverse_result(width=None)) is None  # size unknown
    # Commons is searched directly, with fuller credits.
    assert openverse_candidate(openverse_result(source="wikimedia")) is None


def check(**fields: Any) -> ImageCheck:
    base: dict[str, Any] = {
        "seen": "Eggs poached in a red tomato sauce in a pan.",
        "dish": "yes",
        "finished_dish": True,
        "clash": None,
        "watermark_or_text": False,
        "faces": False,
    }
    return ImageCheck.model_validate(base | fields)


def test_a_close_dish_passes_but_any_problem_fails() -> None:
    assert passes(check())
    assert passes(check(dish="close"))
    assert not passes(check(dish="no"))
    assert not passes(check(clash="bacon on a vegetarian dish"))
    assert not passes(check(finished_dish=False))
    assert not passes(check(watermark_or_text=True))
    assert not passes(check(faces=True))
    assert passes(check(clash="  "))  # an empty answer isn't a clash


def test_long_titles_are_searched_again_in_shorter_forms() -> None:
    assert queries("Classic beef lasagne") == ["Classic beef lasagne", "beef lasagne"]
    assert queries("Prawn linguine with chilli") == [
        "Prawn linguine with chilli",
        "Prawn linguine",
    ]
    assert queries("Oi muchim (cucumber salad)") == ["Oi muchim"]
    assert queries("Albóndigas in tomato sauce") == ["Albóndigas in tomato sauce", "Albóndigas"]
    assert queries("Chicken and chickpea curry")[-1] == "chickpea curry"


def test_a_photo_titled_with_a_meat_the_recipe_lacks_fails() -> None:
    falafel = PASTA.model_copy(update={"title": "Falafel wraps", "ingredients": ["chickpeas"]})
    assert title_clash(falafel, "Dinner: Lamb Koftas with salad (4816).jpg")
    assert title_clash(falafel, "Prawns_on_rice.jpg")
    assert title_clash(falafel, "Falafel wrap at a market.jpg") is None
    fajitas = PASTA.model_copy(
        update={"title": "Chicken fajitas", "ingredients": ["500 g chicken thigh"]}
    )
    assert title_clash(fajitas, "Beef and chicken fajitas.jpg") == "the photo's title says beef"
    assert title_clash(fajitas, "Chicken fajitas, Austin.jpg") is None
    assert title_clash(fajitas, "Hamburg street food.jpg") is None  # whole words only
