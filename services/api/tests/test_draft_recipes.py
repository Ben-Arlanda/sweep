"""The gate on Claude's drafts of new Seed Recipes. No model calls."""

from typing import Any

from scripts.draft_recipes import FullDraft, gate, slug_of, to_seed

DISH = {"title": "Garlic chicken", "cuisine": "australian", "course": "main", "minutes": 25}
STEPS = [
    "Heat the olive oil in a frying pan over medium-high heat.",
    "Fry the chicken for 12 minutes, turning once, until cooked through.",
    "Stir in the garlic for the last minute until fragrant, then serve.",
]


def draft(**overrides: object) -> FullDraft:
    fields: dict[str, Any] = {
        "title": "Garlic chicken",
        "summary": "Chicken thighs fried with garlic.",
        "servings": 4,
        "prep_minutes": 5,
        "cook_minutes": 20,
        "difficulty": "easy",
        "ingredients": ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil"],
        "stages": [
            {"title": "Prep", "minutes": 5, "steps": ["Crush the garlic."]},
            {"title": "Fry the chicken", "minutes": 20, "steps": STEPS},
        ],
        "quick_steps": STEPS,
        "tips": ["Thighs stay juicier than breast."],
        "variations": ["Add chilli."],
        "storage": "Fridge up to 3 days.",
    }
    return FullDraft.model_validate(fields | overrides)


def test_a_sound_draft_passes() -> None:
    assert gate(DISH, draft(), []) == ([], [])


def test_stage_minutes_must_add_up_to_the_total() -> None:
    problems, _ = gate(DISH, draft(cook_minutes=40), [])
    assert "stages: minutes add up to 25, but prep + cook is 45" in problems


def test_the_total_must_be_near_the_dish_asked_for() -> None:
    long = draft(
        cook_minutes=80,
        stages=[{"title": "Fry the chicken", "minutes": 85, "steps": STEPS}],
    )
    problems, _ = gate(DISH, long, [])
    assert "time: 85 min, but this dish should take ~25" in problems


def test_quick_steps_must_be_cookable() -> None:
    vague = ["Fry the chicken in the olive oil.", "Add the garlic.", "Serve."]
    problems, _ = gate(DISH, draft(quick_steps=vague), [])
    assert any(p.startswith("quick steps: no_heat") for p in problems), problems
    assert any(p.startswith("quick steps: no_time") for p in problems), problems


def test_quick_view_has_three_to_six_short_steps() -> None:
    problems, _ = gate(DISH, draft(quick_steps=STEPS[:2]), [])
    assert "quick steps: 2 steps, need 3–6" in problems
    wordy = [*STEPS[:2], STEPS[2] + " word" * 40]
    assert any("words (at most 40)" in p for p in gate(DISH, draft(quick_steps=wordy), [])[0])


def test_an_unknown_ingredient_is_a_new_starter_not_a_retry() -> None:
    lines = ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil"]
    odd = draft(ingredients=[*lines, "1 tbsp zorblax relish"])
    problems, unparsed = gate(DISH, odd, [])
    assert not any("unparsed" in p for p in problems)
    assert unparsed == ["'1 tbsp zorblax relish' matches no Ingredient"]


def test_a_dish_already_in_the_library_is_a_duplicate() -> None:
    existing = to_seed(DISH, draft()).model_copy(update={"slug": "garlic-chicken-old"})
    problems, _ = gate(DISH, draft(), [existing])
    assert any(p.startswith("stages: duplicate") for p in problems), problems


def test_slugs_drop_accents() -> None:
    assert slug_of("Pollo a la brasa") == "pollo-a-la-brasa"
    assert slug_of("Phở gà") == "pho-ga"
