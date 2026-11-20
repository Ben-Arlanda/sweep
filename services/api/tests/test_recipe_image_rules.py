"""The plain-code rules for Recipe Images (slice 4f, ADR 0029). No network, no model."""

from typing import Any

from app.data.recipe_images import sized, with_utm
from app.services.recipe_image_check import ImageCheck, passes, title_clash
from scripts.recipe_images import option, picked, queries
from tests.test_recipes import PASTA

FALAFEL = PASTA.model_copy(update={"title": "Falafel wraps", "ingredients": ["chickpeas"]})


def unsplash(**fields: Any) -> dict[str, Any]:
    return {
        "id": "abc123",
        "width": 5000,
        "height": 3333,
        "description": None,
        "alt_description": "falafel wrap with salad on a plate",
        "urls": {"raw": "https://images.unsplash.com/photo-1?ixid=M3xyz&ixlib=rb-4.1.0"},
        "links": {
            "html": "https://unsplash.com/photos/falafel-abc123",
            "download_location": "https://api.unsplash.com/photos/abc123/download?ixid=M3xyz",
        },
        "user": {
            "name": "Ana  Cook",
            "username": "anacook",
            "links": {"html": "https://unsplash.com/@anacook"},
        },
    } | fields


def test_an_unsplash_result_becomes_an_option_with_its_credit() -> None:
    found = option(unsplash(), FALAFEL)
    assert found is not None
    assert (found.photo_id, found.author) == ("abc123", "Ana Cook")
    assert found.author_url == "https://unsplash.com/@anacook"
    assert found.raw_url.startswith("https://images.unsplash.com/")


def test_options_whose_words_name_a_missing_meat_or_are_small_are_dropped() -> None:
    assert option(unsplash(alt_description="lamb kofta with yoghurt"), FALAFEL) is None
    assert option(unsplash(description="Prawns on rice"), FALAFEL) is None
    assert option(unsplash(width=1000, height=800), FALAFEL) is None


def test_photos_are_sized_by_unsplash_keeping_ixid() -> None:
    url = sized("https://images.unsplash.com/photo-1?ixid=M3xyz&ixlib=rb-4.1.0", 360)
    assert url.startswith("https://images.unsplash.com/photo-1?ixid=M3xyz")
    assert "&w=360&h=270&fit=crop" in url


def test_links_back_carry_unsplash_referral_tags() -> None:
    assert with_utm("https://unsplash.com/@anacook") == (
        "https://unsplash.com/@anacook?utm_source=sweep&utm_medium=referral"
    )
    assert with_utm("https://x.test/?a=1").endswith("?a=1&utm_source=sweep&utm_medium=referral")


def test_long_titles_are_searched_again_in_shorter_forms() -> None:
    assert queries("Classic beef lasagne") == ["Classic beef lasagne", "beef lasagne"]
    assert queries("Prawn linguine with chilli") == [
        "Prawn linguine with chilli",
        "Prawn linguine",
    ]
    assert queries("Oi muchim (cucumber salad)") == ["Oi muchim"]
    assert queries("Albóndigas in tomato sauce") == ["Albóndigas in tomato sauce", "Albóndigas"]
    assert queries("Chicken and chickpea curry")[-1] == "chickpea curry"


def test_words_naming_a_meat_the_recipe_lacks_rule_a_photo_out() -> None:
    assert title_clash(FALAFEL, "Dinner: Lamb Koftas with salad (4816).jpg")
    assert title_clash(FALAFEL, "Prawns_on_rice.jpg")
    assert title_clash(FALAFEL, "Falafel wrap at a market.jpg") is None
    fajitas = PASTA.model_copy(
        update={"title": "Chicken fajitas", "ingredients": ["500 g chicken thigh"]}
    )
    assert title_clash(fajitas, "Beef and chicken fajitas.jpg") == "the photo's title says beef"
    assert title_clash(fajitas, "Chicken fajitas, Austin.jpg") is None
    assert title_clash(fajitas, "Hamburg street food.jpg") is None  # whole words only


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


def test_the_parked_vision_check_passes_close_dishes_but_no_problem() -> None:
    assert passes(check())
    assert passes(check(dish="close"))
    assert not passes(check(dish="no"))
    assert not passes(check(clash="bacon on a vegetarian dish"))
    assert not passes(check(finished_dish=False))
    assert not passes(check(watermark_or_text=True))
    assert not passes(check(faces=True))
    assert passes(check(clash="  "))  # an empty answer isn't a clash


def test_the_first_option_is_picked_unless_the_product_owner_changed_it() -> None:
    found = {"a": {"options": [{"photo_id": "p1"}, {"photo_id": "p2"}]}, "b": {"options": []}}
    assert picked("a", found, {}) == "p1"
    assert picked("a", found, {"a": "p2"}) == "p2"
    assert picked("a", found, {"a": None}) is None  # "No photo"
    assert picked("b", found, {}) is None
