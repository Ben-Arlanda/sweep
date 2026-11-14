"""Automatic checks on Seed Recipes (slice 4c). Plain code: no database, no LLM."""

from app.data.recipes import SeedRecipe, load_seed_recipes
from app.services.recipe_checks import check_recipes


def recipe(**overrides: object) -> SeedRecipe:
    base: dict[str, object] = {
        "slug": "garlic-chicken",
        "title": "Garlic chicken",
        "cuisine": "australian",
        "servings": 4,
        "minutes": 30,
        "summary": "Chicken thighs fried with garlic.",
        "ingredients": ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil"],
        "method": [
            "Fry the chicken in the olive oil for 12 minutes until cooked through.",
            "Add the garlic for the last minute.",
        ],
    }
    return SeedRecipe.model_validate(base | overrides)


def kinds(recipes: list[SeedRecipe]) -> list[str]:
    return [p.check for p in check_recipes(recipes)]


def test_a_sound_recipe_passes() -> None:
    assert check_recipes([recipe()]) == []


def test_a_line_that_matches_no_ingredient_is_flagged() -> None:
    lines = ["600 g chicken thigh", "2 cloves garlic", "1 tbsp olive oil", "1 tbsp unicorn dust"]
    assert kinds([recipe(ingredients=lines)]) == ["unparsed"]


def test_water_needs_no_ingredient() -> None:
    lines = ["600 g chicken thigh", "2 cloves garlic", "1 tbsp olive oil", "250 ml water"]
    assert check_recipes([recipe(ingredients=lines)]) == []


def test_the_method_using_something_not_listed_is_flagged() -> None:
    method = [
        "Fry the chicken in the olive oil for 12 minutes until cooked through.",
        "Add the garlic and parmesan.",
    ]
    problems = check_recipes([recipe(method=method)])
    assert [(p.check, p.message) for p in problems] == [
        ("unlisted", "the method uses parmesan, which isn't in the ingredients")
    ]


def test_the_longest_name_wins_so_rice_noodles_are_not_rice() -> None:
    lines = ["200 g rice noodles", "1 tbsp soy sauce"]
    method = ["Soak the rice noodles for 5 minutes, then toss with the soy sauce."]
    assert kinds([recipe(ingredients=lines, method=method)]) == []


def test_aliases_count_as_the_ingredient() -> None:
    # "spring onions" listed; method says "spring onion" (a variant) and "pepper" = black pepper
    lines = ["600 g chicken thigh", "2 spring onions, sliced", "1 tsp black pepper"]
    method = [
        "Grill the chicken for 15 minutes until cooked through, with the pepper.",
        "Scatter with spring onion.",
    ]
    assert kinds([recipe(ingredients=lines, method=method)]) == []


def test_raw_meat_without_a_proper_cooking_step_is_flagged() -> None:
    method = ["Toss the chicken with the garlic and olive oil and serve."]
    assert kinds([recipe(method=method)]) == ["raw_meat"]


def test_a_cooking_step_needs_a_time_or_a_doneness_cue() -> None:
    method = ["Fry the chicken in the olive oil with the garlic."]
    assert kinds([recipe(method=method)]) == ["raw_meat"]
    cooked = ["Fry the chicken in the olive oil with the garlic until no longer pink."]
    assert kinds([recipe(method=cooked)]) == []


def test_ready_to_eat_meat_needs_no_cooking() -> None:
    lines = ["200 g ham", "4 slices bread", "20 g butter"]
    method = ["Butter the bread and fill with the ham."]
    assert kinds([recipe(ingredients=lines, method=method, minutes=5)]) == []


def test_a_step_longer_than_the_whole_recipe_is_flagged() -> None:
    method = ["Braise the chicken with the garlic and olive oil for 2 hours."]
    assert kinds([recipe(method=method, minutes=45)]) == ["timing"]


def test_two_recipes_with_the_same_title_are_flagged() -> None:
    twin = recipe(slug="garlic-chicken-2", title="Garlic Chicken")
    assert kinds([recipe(), twin]) == ["duplicate"]


def test_near_identical_ingredients_in_the_same_cuisine_are_flagged() -> None:
    twin = recipe(slug="chicken-with-garlic", title="Chicken with garlic")
    assert kinds([recipe(), twin]) == ["duplicate"]


def test_every_seed_recipe_passes_the_checks() -> None:
    # The gate for the real library: a new recipe can't land until it passes.
    problems = check_recipes(load_seed_recipes())
    assert [f"{p.slug}: {p.check}: {p.message}" for p in problems] == []


def test_steaming_counts_as_cooking() -> None:
    lines = ["4 white fish fillets", "1 tbsp soy sauce"]
    method = ["Steam the fish for 8 minutes until it flakes, then drizzle with the soy sauce."]
    assert kinds([recipe(ingredients=lines, method=method, minutes=15)]) == []


def test_a_vegetarian_claim_with_meat_or_hidden_seafood_is_flagged() -> None:
    lines = ["2 tbsp green curry paste", "400 ml coconut milk", "300 g tofu"]
    method = ["Simmer the tofu in the curry paste and coconut milk for 10 minutes."]
    curry = recipe(ingredients=lines, method=method, summary="Tofu curry. Vegetarian.")
    assert [(p.check, p.message) for p in check_recipes([curry])] == [
        ("diet_claim", "says vegetarian but has green curry paste")
    ]


def test_a_vegan_claim_with_dairy_or_eggs_is_flagged() -> None:
    lines = ["400 g pasta", "40 g parmesan, grated", "1 tbsp olive oil"]
    method = ["Cook the pasta for 10 minutes and toss with the oil and parmesan."]
    pasta = recipe(ingredients=lines, method=method, summary="Simple pasta. Vegan.")
    assert kinds([pasta]) == ["diet_claim"]


def test_a_hedged_or_honest_diet_note_is_fine() -> None:
    lines = ["2 tbsp green curry paste", "400 ml coconut milk", "300 g tofu"]
    method = ["Simmer the tofu in the curry paste and coconut milk for 10 minutes."]
    hedged = recipe(
        ingredients=lines, method=method, summary="Tofu curry. Vegetarian if the paste is."
    )
    assert check_recipes([hedged]) == []


def test_an_odd_free_phrase_is_flagged_but_diet_words_are_not() -> None:
    odd = recipe(summary="Chicken with rice and orange-free greens.")
    assert kinds([odd]) == ["odd_phrase"]
    fine = recipe(summary="A gluten-free, dairy-free chicken dinner.")
    assert check_recipes([fine]) == []
