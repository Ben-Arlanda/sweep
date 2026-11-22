"""Reading recipe ingredient lines with plain rules (no database, no LLM)."""

from collections.abc import Sequence
from decimal import Decimal

import pytest

from app.data.ingredients import INGREDIENTS
from app.models import ParseMethod
from app.services.ingredient_lines import (
    IngredientIndex,
    LineReading,
    normalise_lines,
    parse_line,
    parse_lines,
)

D = Decimal
INDEX = IngredientIndex.from_seed(INGREDIENTS)


@pytest.mark.parametrize(
    ("text", "ingredient", "quantity", "unit", "note"),
    [
        ("500 g beef mince", "beef mince", D("500"), "g", None),
        ("500g beef mince", "beef mince", D("500"), "g", None),
        ("1 onion, finely diced", "onion", D("1"), None, "finely diced"),
        ("2 tbsp olive oil", "olive oil", D("2"), "tbsp", None),
        ("2 tablespoons olive oil", "olive oil", D("2"), "tbsp", None),
        ("1 1/2 cups plain flour", "plain flour", D("1.5"), "cup", None),
        ("1½ cups plain flour", "plain flour", D("1.5"), "cup", None),
        ("½ tsp ground cumin", "ground cumin", D("0.5"), "tsp", None),
        # "garlic cloves" is also an alias, but garlic is counted in bulbs: 3 cloves ≠ 3 bulbs
        ("3 garlic cloves, crushed", "garlic", D("3"), "clove", "crushed"),
        ("3 cloves garlic, crushed", "garlic", D("3"), "clove", "crushed"),
        ("400 g can chickpeas, drained", "chickpeas", D("400"), "g", "drained"),
        ("2 x 400 g cans canned tomatoes", "canned tomatoes", D("800"), "g", None),
        ("2-3 large potatoes", "potatoes", D("3"), None, None),  # a range: buy for the top
        ("1 bunch coriander (leaves picked)", "coriander", D("1"), "bunch", "leaves picked"),
        ("1 lemon, juiced", "lemons", D("1"), None, "juiced"),
        ("salt, to taste", "salt", None, None, "to taste"),
        ("2 sticks celery, diced", "celery", D("2"), "stick", "diced"),
        ("4 lettuce leaves", "lettuce", D("4"), "leaf", None),
        ("2 bay leaves", "bay leaves", D("2"), None, None),  # "leaves" is part of the name
        ("1 loaf crusty bread", "bread", D("1"), "loaf", None),
        ("3 sheets puff pastry", "puff pastry", D("3"), "sheet", None),
        ("300 g cooked prawns", "cooked prawns", D("300"), "g", None),  # sold cooked
        ("Eggs", "eggs", None, None, None),
        # RecipeTin Eats style (print-to-PDF, 2026-11-17): metric first, imperial after a
        # slash. Keep the metric amount; the imperial one is the same thing.
        (
            "4 x 180g/6 oz salmon fillets, skin on or off, doesn't matter (Note 1)",
            "salmon fillet",
            D("720"),
            "g",
            "skin on or off, doesn't matter; Note 1",
        ),
        (
            "200g/ 7 oz cherry tomatoes (or grape tomatoes, 1 Aussie punnet)",
            "cherry tomatoes",
            D("200"),
            "g",
            "or grape tomatoes, 1 Aussie punnet",
        ),
        ("500g/1 lb beef mince", "beef mince", D("500"), "g", None),
        ("1/2 tsp cooking salt / kosher salt", "salt", D("0.5"), "tsp", None),
        ("1 tsp lemon zest (1 lemon)", "lemons", D("1"), "tsp", "1 lemon"),
        ("1 tbsp lemon juice", "lemons", D("1"), "tbsp", None),
        ("Lemon wedges or slices, optional", "lemons", None, None, None),
        ("2 tbsp lime juice", "limes", D("2"), "tbsp", None),
        ("1 tsp white sesame seeds", "sesame seeds", D("1"), "tsp", None),
        (
            "1/2 tsp black sesame seeds (or more white)",
            "sesame seeds",
            D("0.5"),
            "tsp",
            "or more white",
        ),
        ("Olive oil spray", "olive oil", None, None, None),
        (
            "1/3 cup pickled jalapeno, roughly chopped",
            "pickled jalapenos",
            D("0.333"),
            "cup",
            "roughly chopped",
        ),
        ("2 jalapeños, sliced", "jalapenos", D("2"), None, "sliced"),
        ("1.5 kg pork ribs", "pork ribs", D("1.5"), "kg", None),
        ("1 tbsp apple cider vinegar", "apple cider vinegar", D("1"), "tbsp", None),
        ("1 packet taco seasoning", "taco seasoning", D("1"), None, None),
        ("8 taco shells", "taco shells", D("8"), None, None),
    ],
)
def test_reads_quantity_unit_name_and_note(
    text: str, ingredient: str, quantity: Decimal | None, unit: str | None, note: str | None
) -> None:
    line = parse_line(text, INDEX)
    assert line.ingredient is not None, f"no Ingredient for {text!r}"
    assert line.ingredient.name == ingredient
    assert (line.quantity, line.unit, line.note) == (quantity, unit, note)
    assert line.method == ParseMethod.RULE
    assert not line.needs_review


@pytest.mark.parametrize(
    ("text", "base_quantity"),
    [
        ("2 tbsp olive oil", D("40")),  # Australian tablespoon = 20 ml; olive oil is kept in ml
        ("1 cup plain flour", D("132.5")),  # 250 ml × 0.53 g/ml
        ("1 kg potatoes", D("1000")),
        ("2 eggs", D("2")),
        ("1 tsp ground cumin", None),  # no density for cumin: don't guess grams
        ("3 cloves garlic", None),  # garlic is counted in bulbs; cloves don't convert
        ("2 potatoes", None),  # potatoes are weighed; a count isn't a weight
        ("1 lb beef mince", D("453.592")),  # US recipes, via URL import
        ("8 oz. mushrooms", D("226.796")),
        ("3 sheets puff pastry", D("3")),  # pastry is counted in sheets
        # 4 cups of *cooked* rice is about 1⅓ cups dry: matching rice is right, but the
        # amount isn't an amount of what you'd buy.
        ("4 cups cooked rice", None),
    ],
)
def test_converts_to_the_ingredients_own_unit_only_when_honest(
    text: str, base_quantity: Decimal | None
) -> None:
    assert parse_line(text, INDEX).base_quantity == base_quantity


# Real recipe sites write lines our Seed Recipes never do (found by evals.link_import,
# 2026-11-16: 31 of 36 lines from four sites were Not linked). Reworded here, same shapes.
@pytest.mark.parametrize(
    ("text", "ingredient", "quantity", "unit", "note"),
    [
        # Preparation words without a comma
        ("1 onion finely chopped", "onion", D("1"), None, "finely chopped"),
        ("2 garlic cloves crushed", "garlic", D("2"), "clove", "crushed"),  # cloves, not bulbs
        ("1 large zucchini peeled into ribbons", "zucchini", D("1"), None, "peeled into ribbons"),
        ("½ a lemon zested and juiced", "lemons", D("0.5"), None, "zested and juiced"),
        # ...or in front of the name
        ("1 cup finely grated parmesan", "parmesan", D("1"), "cup", "finely grated"),
        ("grated parmesan to serve", "parmesan", None, None, "grated; to serve"),
        # Hyphens, frozen, "X or Y", loose measures
        ("60 ml extra-virgin olive oil", "olive oil", D("60"), "ml", None),
        ("½ frozen banana", "bananas", D("0.5"), None, None),
        ("1 cup frozen spinach or kale", "baby spinach", D("1"), "cup", "or kale"),
        ("3 cups chicken or vegetable stock", "chicken stock", D("3"), "cup", "or vegetable stock"),
        ("large handful parsley leaves chopped", "parsley", None, None, "chopped"),
        ("2 tbsp basil leaves", "basil", D("2"), "tbsp", None),
        # New starters and aliases (2026-11-16)
        ("1 tsp fennel seeds", "fennel seeds", D("1"), "tsp", None),
        ("1 kg baby calamari", "squid", D("1"), "kg", None),
        ("1 cup almond milk", "almond milk", D("1"), "cup", None),
        ("½ tablespoon almond butter", "almond butter", D("0.5"), "tbsp", None),
        ("1 tsp chia seeds", "chia seeds", D("1"), "tsp", None),
        ("1 cup instant polenta", "polenta", D("1"), "cup", None),
        ("70 g greek-style yoghurt", "greek yoghurt", D("70"), "g", None),
        ("80 gm mixed olives", "kalamata olives", D("80"), "g", None),  # "gm" for grams
        # Older cookbooks and typed-up family recipes (a real cookbook photo, 2026-11-16)
        ("1 tablespoonful of curry powder", "curry powder", D("1"), "tbsp", None),
        ("1 teaspoonful of salt", "salt", D("1"), "tsp", None),
        ("3 tablespoonfuls of yoghurt", "greek yoghurt", D("3"), "tbsp", None),
        ("1 teacupful of water", None, D("1"), "cup", None),
        ("2 tablespoonfuls of oil", "vegetable oil", D("2"), "tbsp", None),
        ("5 strands of coriander, chopped", "coriander", D("5"), "sprig", "chopped"),
        ("1 inch cube of ginger, grated", "ginger", D("1"), "inch", "grated"),
        ("2 cm piece ginger", "ginger", D("2"), "cm", None),
        ("6 curry leaves if you can get them", "curry leaves", D("6"), None, "if you can get them"),
        ("salt flakes, to serve", "salt", None, None, "to serve"),
        ("cooking oil spray", "vegetable oil", None, None, None),
        # Slice 4g's library: what it's for, and words that describe the thing
        ("neutral oil for frying", "vegetable oil", None, None, "for frying"),
        ("1 egg for batter", "eggs", D("1"), None, "for batter"),
        ("600 g boneless chicken thighs", "chicken thigh", D("600"), "g", None),
        ("500 g raw peeled prawns", "prawns", D("500"), "g", "peeled"),
        ("1 tbsp toasted sesame seeds", "sesame seeds", D("1"), "tbsp", None),
        ("2 firm pears", "pears", D("2"), None, None),
        ("1 tsp fine salt", "salt", D("1"), "tsp", None),
        ("250 ml lukewarm water", None, D("250"), "ml", None),
        ("4 celery stalks", "celery", D("4"), "stalk", None),
        ("2 rosemary sprigs", "rosemary", D("2"), "sprig", None),
        ("6 filo pastry sheets", "filo pastry", D("6"), "sheet", None),
        ("4 thick slices sourdough", "bread", D("4"), "slice", None),
        ("2 shots hot espresso", "coffee", D("2"), "shot", None),
        ("200 g soaked dried chickpeas", "chickpeas", D("200"), "g", "soaked"),
    ],
)
def test_reads_lines_the_way_recipe_websites_write_them(
    text: str,
    ingredient: str | None,
    quantity: Decimal | None,
    unit: str | None,
    note: str | None,
) -> None:
    line = parse_line(text, INDEX)
    assert (line.ingredient.name if line.ingredient else None) == ingredient, text
    assert (line.quantity, line.unit, line.note) == (quantity, unit, note)
    assert not line.needs_review


# An imported Jambalaya (RecipeTin Eats, 2026-11-21): 7 of 22 lines were Not linked.
@pytest.mark.parametrize(
    ("text", "ingredient", "quantity", "unit", "note"),
    [
        # Nested notes left a stray ")" in the name; "or" names the other choice
        (
            '200g (7oz) andouille or smoked sausage (, sliced 0.5cm / 1/5" thick (Note 1))',
            "smoked sausage",
            D("200"),
            "g",
            'or andouille sausage; 7oz; sliced 0.5cm / 1/5" thick; Note 1',
        ),
        (
            '2 celery ribs (, cut into 1.5 cm / 0.5" pieces)',
            "celery",
            D("2"),
            "stalk",
            'cut into 1.5 cm / 0.5" pieces',
        ),
        (
            "1.25 cups long grain rice (, uncooked (Note 2))",
            "rice",
            D("1.25"),
            "cup",
            "uncooked; Note 2",
        ),
        # "broth / stock" are both chicken stock, so no "or"; "low-sodium" is worth keeping
        (
            "2.5 cups (625ml) low-sodium chicken broth / stock ((Note 3))",
            "chicken stock",
            D("2.5"),
            "cup",
            "low-sodium; 625ml; Note 3",
        ),
        ("4 tsp sweet paprika", "paprika", D("4"), "tsp", None),
        ("1 tsp onion powder", "onion powder", D("1"), "tsp", None),
        (
            "1/2 tsp cayenne powder ((adjust spice to taste))",
            "cayenne pepper",
            D("0.5"),
            "tsp",
            "adjust spice to taste",
        ),
        # Brackets someone forgot to close
        ("1 cup rice (Note 1", "rice", D("1"), "cup", "Note 1"),
    ],
)
def test_reads_the_jambalaya_lines_it_used_to_miss(
    text: str, ingredient: str, quantity: Decimal, unit: str, note: str
) -> None:
    line = parse_line(text, INDEX)
    assert line.ingredient is not None and line.ingredient.name == ingredient, text
    assert (line.quantity, line.unit, line.note) == (quantity, unit, note)
    assert "(" not in line.name and ")" not in line.name


def test_the_new_rules_only_run_when_the_old_ones_found_nothing() -> None:
    # "frozen peas" is a starter: stripping "frozen" first would have lost it.
    assert parse_line("1 cup frozen peas", INDEX).ingredient.name == "frozen peas"  # type: ignore[union-attr]
    # Canned products keep their identity: crushed tomatoes come in a can.
    crushed = parse_line("2 x 400g cans crushed tomatoes", INDEX)
    assert crushed.ingredient is not None and crushed.ingredient.name == "canned tomatoes"
    # Loose words go, and what's left can still be something nobody shops for.
    ice = parse_line("handful of ice", INDEX)
    assert (ice.ingredient, ice.needs_review) == (None, False)
    # Steamed rice is cooked rice: rice, with an amount you wouldn't buy.
    steamed = parse_line("2 cups steamed jasmine rice", INDEX)
    assert steamed.ingredient is not None and steamed.ingredient.name == "rice"
    assert steamed.prepared
    # Still no guessing: an unknown thing stays unknown.
    assert parse_line("2 tbsp finely chopped unobtainium", INDEX).needs_review


@pytest.mark.parametrize(
    ("text", "name", "note"),
    [
        ("200 g andouille sausage, sliced", "andouille sausage", "sliced"),
        ("2 tbsp finely chopped zorblax", "zorblax", "finely chopped"),
        ("1 cup low-sodium glorp stock (Note 1)", "glorp stock", "low-sodium; Note 1"),
        ("1 zorblax finely sliced", "zorblax", "finely sliced"),
        ("1 cup zorblax or glorp", "zorblax", "or glorp"),
    ],
)
def test_a_line_it_cannot_match_still_gets_a_clean_name(text: str, name: str, note: str) -> None:
    # The name a new Household Ingredient will get (ADR 0032), so no "finely chopped zorblax"
    line = parse_line(text, INDEX)
    assert (line.ingredient, line.needs_review) == (None, True)
    assert (line.name, line.note) == (name, note)


# ADR 0032: "salt and pepper" is two things to have, not one new food
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("salt and pepper", [("salt", None, None, None), ("black pepper", None, None, None)]),
        (
            "Salt and pepper, to taste",
            [("salt", None, None, "to taste"), ("black pepper", None, None, "to taste")],
        ),
        # One amount for both: it can't be given to either
        (
            "2 tbsp salt and pepper",
            [("salt", None, None, None), ("black pepper", None, None, None)],
        ),
        # Each has its own amount
        (
            "1 onion and 2 carrots, diced",
            [("onion", D("1"), None, "diced"), ("carrots", D("2"), None, "diced")],
        ),
        # "each": the amount is for both (RecipeTin Eats salmon tray bake, 2026-11-22)
        (
            "1/4 tsp each salt and pepper",
            [("salt", D("0.25"), "tsp", None), ("black pepper", D("0.25"), "tsp", None)],
        ),
        (
            "salt and freshly ground black pepper",
            [("salt", None, None, None), ("black pepper", None, None, "freshly")],
        ),
    ],
)
def test_two_known_foods_joined_by_and_are_two_lines(
    text: str, expected: list[tuple[str, Decimal | None, str | None, str | None]]
) -> None:
    lines = parse_lines(text, INDEX)
    got = [(x.ingredient.name if x.ingredient else None, x.quantity, x.unit, x.note) for x in lines]
    assert got == expected
    assert all(x.raw_text == text for x in lines)  # both keep what was written


@pytest.mark.parametrize(
    "text",
    ["salt and vinegar chips", "2 eggs", "1 zorblax and 1 onion", "salt (and pepper)"],
)
def test_and_only_splits_when_both_sides_are_known(text: str) -> None:
    assert parse_lines(text, INDEX) == [parse_line(text, INDEX)]


def test_flags_lines_it_cannot_match_instead_of_guessing() -> None:
    line = parse_line("1 cup unobtainium shavings", INDEX)
    assert line.ingredient is None
    assert line.needs_review
    assert (line.quantity, line.unit) == (D("1"), "cup")


def test_water_is_not_something_you_shop_for() -> None:
    line = parse_line("1 cup boiling water", INDEX)
    assert line.ingredient is None
    assert not line.needs_review


def test_marks_optional_lines() -> None:
    assert parse_line("1 tsp chilli flakes (optional)", INDEX).optional
    assert not parse_line("1 tsp chilli flakes", INDEX).optional
    # "optional" among other notes (RecipeTin Eats salmon tray bake, 2026-11-22)
    parsley = parse_line("Parsley, finely chopped, optional", INDEX)
    assert (parsley.optional, parsley.note) == (True, "finely chopped")


class ScriptedParser:
    """A fake LLM: returns readings we choose, and records what it was asked."""

    def __init__(self, readings: list[LineReading]) -> None:
        self.readings = readings
        self.asked: list[str] = []

    async def read_lines(
        self, lines: Sequence[str], ingredient_names: Sequence[str], units: Sequence[str]
    ) -> list[LineReading]:
        self.asked = list(lines)
        return self.readings


@pytest.mark.anyio
async def test_only_lines_the_rules_missed_go_to_the_llm() -> None:
    llm = ScriptedParser(
        [LineReading(line=0, quantity=1, unit=None, ingredient="lemons", note="juice only")]
    )
    lines = ["2 eggs", "juice of 1 lemon"]
    eggs, lemon = await normalise_lines(lines, INDEX, llm)

    assert llm.asked == ["juice of 1 lemon"]
    assert eggs.method == ParseMethod.RULE
    assert lemon.method == ParseMethod.LLM
    assert lemon.ingredient is not None and lemon.ingredient.name == "lemons"
    assert (lemon.quantity, lemon.base_quantity, lemon.note) == (D("1"), D("1"), "juice only")
    assert not lemon.needs_review


@pytest.mark.anyio
async def test_llm_answers_are_checked_against_our_lists() -> None:
    llm = ScriptedParser(
        [
            # Not one of our Ingredients: refused, the line stays flagged.
            LineReading(line=0, quantity=2, unit="cup", ingredient="dragon fruit", note=None),
            # Ours, but with a unit we don't know: keep the Ingredient, drop the unit.
            LineReading(line=1, quantity=3, unit="smidgen", ingredient="butter", note=None),
            # A line number we never sent: ignored.
            LineReading(line=7, quantity=1, unit=None, ingredient="salt", note=None),
        ]
    )
    dragon, butter = await normalise_lines(["2 c. pitaya", "3 knobs of butta"], INDEX, llm)
    assert dragon.ingredient is None and dragon.needs_review
    assert butter.ingredient is not None and butter.ingredient.name == "butter"
    assert (butter.unit, butter.base_quantity) == (None, None)  # 3 of what? we don't know


def test_a_beef_stock_cube_is_left_for_a_person() -> None:
    # "stock cubes" are only "check the label" for meat, so linking a *beef* stock cube
    # to them would let it past a vegetarian Rule. Not linked fails closed instead.
    assert parse_line("1 beef stock cube, crumbled", INDEX).needs_review
