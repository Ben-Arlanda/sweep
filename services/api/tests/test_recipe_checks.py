"""Automatic checks on Seed Recipes (slice 4c). Plain code: no database, no LLM."""

from app.data.recipes import SeedRecipe, load_seed_recipes
from app.services.recipe_checks import check_recipes


def recipe(**overrides: object) -> SeedRecipe:
    base: dict[str, object] = {
        "slug": "garlic-chicken",
        "title": "Garlic chicken",
        "cuisine": "australian",
        "course": "main",
        "servings": 4,
        "minutes": 30,
        "summary": "Chicken thighs fried with garlic.",
        "ingredients": ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil"],
        "method": [
            "Fry the chicken in the olive oil over medium-high heat for 12 minutes until cooked"
            " through.",
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
        "Fry the chicken in the olive oil over medium heat for 12 minutes until cooked through.",
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
    method = ["Fry the chicken in the olive oil over medium heat with the garlic."]
    assert kinds([recipe(method=method)]) == ["raw_meat", "no_time"]
    cooked = [
        "Fry the chicken in the olive oil over medium heat with the garlic until no longer pink."
    ]
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
    method = ["Cook the pasta in boiling water for 10 minutes and toss with the oil and parmesan."]
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


# --- Cookable Method (slice 4e) -------------------------------------------------------


def test_a_listed_ingredient_the_method_never_uses_is_flagged() -> None:
    lines = ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil", "1 lemon"]
    problems = check_recipes([recipe(ingredients=lines)])
    assert [(p.check, p.message) for p in problems] == [
        ("unused", "'1 lemon' isn't used in any step")
    ]


def test_a_word_from_the_line_counts_as_using_it() -> None:
    # "the oil" uses "olive oil"; "the beef" uses "beef mince"
    lines = ["500 g beef mince", "1 tbsp olive oil"]
    method = ["Brown the beef in the oil over high heat for 8 minutes until cooked through."]
    assert check_recipes([recipe(ingredients=lines, method=method)]) == []


def test_a_group_word_uses_its_members() -> None:
    lines = [
        "600 g chicken thigh",
        "1 tbsp olive oil",
        "1 tsp ground cumin",
        "1 tsp paprika",
        "1/2 tsp salt",
        "1/2 tsp black pepper",
        "1 bunch coriander, chopped",
    ]
    method = [
        "Rub the chicken with the spices, season, and fry in the oil over medium heat for"
        " 12 minutes until cooked through.",
        "Scatter with the herbs.",
    ]
    assert check_recipes([recipe(ingredients=lines, method=method)]) == []


def test_everything_does_not_count_as_naming_the_ingredients() -> None:
    lines = ["2 x 400 g cans chickpeas, drained", "1 cucumber, chopped", "2 tbsp olive oil"]
    toss = recipe(ingredients=lines, method=["Toss everything together."], minutes=10)
    assert kinds([toss]) == ["unused", "unused", "unused"]


def test_egg_yolks_and_whites_use_the_eggs() -> None:
    lines = ["3 eggs, separated", "100 g caster sugar"]
    method = ["Whisk the yolks with the sugar, then fold in the whipped whites."]
    assert check_recipes([recipe(ingredients=lines, method=method, minutes=10)]) == []


def test_a_pan_step_needs_a_heat_level() -> None:
    method = [
        "Fry the chicken in the olive oil for 12 minutes until cooked through.",
        "Add the garlic for the last minute.",
    ]
    problems = check_recipes([recipe(method=method)])
    assert [(p.check, p.message) for p in problems] == [
        ("no_heat", "'Fry the chicken in the olive oil for 12…' gives no heat level")
    ]


def test_a_heat_level_carries_forward_to_later_steps() -> None:
    method = [
        "Heat the olive oil in a frying pan over medium heat.",
        "Fry the chicken for 12 minutes until cooked through, adding the garlic at the end.",
    ]
    assert check_recipes([recipe(method=method)]) == []


def test_simmering_boiling_and_a_hot_pan_are_heat_levels() -> None:
    for step in (
        "Sear the chicken in the olive oil in a very hot pan for 4 minutes each side until"
        " cooked through, adding the garlic at the end.",
        "Brown the chicken in the olive oil, then simmer with the garlic for 25 minutes until"
        " cooked through.",
    ):
        assert check_recipes([recipe(method=[step])]) == [], step


def test_boiling_water_is_no_heat_level_for_the_next_pan_step() -> None:
    lines = ["400 g pasta", "2 cloves garlic, sliced", "1 tbsp olive oil"]
    method = [
        "Cook the pasta in boiling water for 10 minutes and drain.",
        "Soften the garlic in the olive oil for 1 minute and toss with the pasta.",
    ]
    assert kinds([recipe(ingredients=lines, method=method, minutes=15)]) == ["no_heat"]


def test_the_oven_temperature_is_no_heat_level_for_the_pan() -> None:
    method = [
        "Heat the oven to 200°C.",
        "Fry the chicken in the olive oil for 12 minutes until cooked through, adding the garlic.",
    ]
    assert kinds([recipe(method=method)]) == ["no_heat"]


def test_toasting_in_a_dry_pan_needs_a_heat_level() -> None:
    lines = ["600 g chicken thigh", "2 cloves garlic, crushed", "1 tbsp olive oil", "40 g walnuts"]
    method = [
        "Toast the walnuts in a dry pan for 4 minutes.",
        "Fry the chicken in the olive oil over medium heat for 12 minutes until cooked through,"
        " adding the garlic.",
    ]
    assert kinds([recipe(ingredients=lines, method=method)]) == ["no_heat"]


def test_baking_needs_an_oven_temperature() -> None:
    lines = ["150 g self-raising flour", "2 eggs", "100 g caster sugar", "100 g butter, melted"]
    method = ["Mix the flour, eggs, sugar and butter.", "Bake for 25 minutes until golden."]
    cake = recipe(ingredients=lines, method=method, minutes=35)
    assert [(p.check, p.message) for p in check_recipes([cake])] == [
        ("no_heat", "'Bake for 25 minutes until golden.' gives no oven temperature")
    ]
    hot = ["Heat the oven to 180°C. Mix the flour, eggs, sugar and butter.", method[1]]
    assert check_recipes([recipe(ingredients=lines, method=hot, minutes=35)]) == []


def test_brown_sugar_is_not_a_browning_step() -> None:
    lines = ["100 g butter", "100 g brown sugar", "150 g plain flour"]
    method = ["Rub the butter into the flour and brown sugar until crumbly."]
    assert kinds([recipe(ingredients=lines, method=method, minutes=10)]) == []


def test_baking_powder_and_fried_eggs_are_not_cooking_steps() -> None:
    lines = ["150 g self-raising flour", "1 tsp baking powder", "250 ml milk", "4 eggs"]
    method = ["Whisk the flour, baking powder and milk into a batter.", "Top with the eggs."]
    assert kinds([recipe(ingredients=lines, method=method, minutes=10)]) == []


def test_a_cooking_step_needs_a_time_or_a_cue() -> None:
    lines = ["1 onion, diced", "2 cloves garlic, crushed", "1 tbsp olive oil"]
    vague = ["Soften the onion and garlic in the olive oil over medium heat."]
    problems = check_recipes([recipe(ingredients=lines, method=vague, minutes=10)])
    assert [p.check for p in problems] == ["no_time"]
    for cue in ("for 6 minutes", "until soft"):
        fixed = [f"Soften the onion and garlic in the olive oil over medium heat {cue}."]
        assert check_recipes([recipe(ingredients=lines, method=fixed, minutes=10)]) == []


def test_a_staple_cooked_by_its_packet_needs_no_time_or_heat() -> None:
    lines = ["300 g rice", "1 tbsp soy sauce"]
    method = ["Cook the rice according to the packet.", "Toss the rice with the soy sauce."]
    assert check_recipes([recipe(ingredients=lines, method=method, minutes=20)]) == []
    bare = ["Cook the rice.", "Toss the rice with the soy sauce."]
    assert kinds([recipe(ingredients=lines, method=bare, minutes=20)]) == ["no_heat", "no_time"]
