"""The gate on Claude's drafts for the new Seed Recipe library (slice 4g). No model calls."""

from typing import Any

from scripts.build_recipe_library import Draft, Stage, gate

SOURCE: dict[str, Any] = {
    "title": "Garlic Chicken",
    "cuisine": "australian",
    "course": "main",
    "servings": 4,
    "prep_minutes": 5,
    "cook_minutes": 20,
    "summary": "Chicken thighs fried with garlic.",
    "ingredients": ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil"],
    "stages": [
        {
            "title": "Fry the chicken",
            "minutes": 15,
            "steps": [
                "Heat the olive oil in a frying pan over medium-high heat.",
                "Fry the chicken for 12 minutes, turning once, until cooked through.",
            ],
        },
        {
            "title": "Add the garlic",
            "minutes": 2,
            "steps": ["Stir in the garlic for the last minute until fragrant."],
        },
    ],
}

QUICK = [
    "Heat the olive oil in a frying pan over medium-high heat.",
    "Fry the chicken for 12 minutes, turning once, until cooked through.",
    "Stir in the garlic for the last minute until fragrant, then serve.",
]


def draft(**overrides: object) -> Draft:
    return Draft.model_validate({"title": "Garlic chicken", "quick_steps": QUICK} | overrides)


def test_a_sound_draft_passes() -> None:
    assert gate(SOURCE, draft()) == []


def test_quick_view_has_three_to_six_steps() -> None:
    assert "quick steps: 2 steps, need 3–6" in gate(SOURCE, draft(quick_steps=QUICK[:2]))
    assert gate(SOURCE, draft(quick_steps=QUICK * 3))[0] == "quick steps: 9 steps, need 3–6"


def test_quick_steps_must_pass_the_cookable_method_checks() -> None:
    vague = ["Fry the chicken in the olive oil.", "Add the garlic.", "Serve."]
    problems = gate(SOURCE, draft(quick_steps=vague))
    assert any(p.startswith("quick steps: no_heat") for p in problems), problems
    assert any(p.startswith("quick steps: no_time") for p in problems), problems


def test_quick_steps_must_use_every_ingredient() -> None:
    no_garlic = [*QUICK[:2], "Rest for 2 minutes, then serve."]
    assert gate(SOURCE, draft(quick_steps=no_garlic)) == [
        "quick steps: unused: '2 cloves garlic, crushed' isn't used in any step"
    ]


def test_the_stages_must_pass_too() -> None:
    bad = {**SOURCE, "stages": [{"title": "Cook", "minutes": 20, "steps": ["Fry it all."]}]}
    assert any(p.startswith("stages: ") for p in gate(bad, draft()))


def test_fixed_stages_must_be_small_edits_of_the_original() -> None:
    stages = [Stage.model_validate(s) for s in SOURCE["stages"]]
    fixed = [
        stages[0],
        stages[1].model_copy(update={"steps": ["Stir in the garlic for 1 minute until fragrant."]}),
    ]
    assert gate(SOURCE, draft(stages=fixed)) == []
    renamed = [stages[0].model_copy(update={"title": "Something else"}), stages[1]]
    assert gate(SOURCE, draft(stages=renamed)) == ["stages: stage titles changed"]
    rewritten = [
        stages[0].model_copy(
            update={
                "steps": [
                    "Grill everything on a barbecue over high heat for 14 minutes until charred."
                ]
            }
        ),
        stages[1],
    ]
    assert gate(SOURCE, draft(stages=rewritten)) == [
        "stages: 'Fry the chicken' rewritten, not fixed"
    ]


def test_ingredient_changes_are_kept_small() -> None:
    lines = [*SOURCE["ingredients"], "Salt"]
    stages = [Stage.model_validate(s) for s in SOURCE["stages"]]
    seasoned = [
        stages[0],
        stages[1].model_copy(update={"steps": [*stages[1].steps, "Season with salt."]}),
    ]
    quick = [
        *QUICK[:2],
        "Stir in the garlic for the last minute until fragrant, then season with salt.",
    ]
    assert gate(SOURCE, draft(ingredients=lines, stages=seasoned, quick_steps=quick)) == []
    swapped = ["500 g beef steak", "1 onion", "2 tbsp butter"]
    assert gate(SOURCE, draft(ingredients=swapped)) == ["ingredients: 3 lines removed (at most 2)"]


def test_quick_steps_stay_short() -> None:
    long = [
        QUICK[0],
        QUICK[1] + " " + "Keep turning it now and then so both sides colour evenly." * 3,
        QUICK[2],
    ]
    assert any(
        p.startswith("quick steps: step 2 has") for p in gate(SOURCE, draft(quick_steps=long))
    )


def test_a_changed_ingredient_line_stays_a_plain_line() -> None:
    chatty = [
        *SOURCE["ingredients"][:2],
        "1 tbsp olive oil (half now for the pan, the rest kept back for the garlic later)",
    ]
    assert gate(SOURCE, draft(ingredients=chatty)) == [f"ingredients: '{chatty[2]}' is too long"]
