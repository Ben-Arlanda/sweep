"""What each Ingredient contains, for Dietary Rules. Reference data, reviewed by a person.

Two lists, because "contains" and "depends on the brand" need different handling:

- CONTAINS: the Ingredient always (or nearly always, in Australian shops) has it. A
  recipe using it breaks the Rule and is filtered out.
- CHECK_LABEL: some brands do and some don't (stock, sausages, curry pastes). Recipes
  using it still pass, but the agent must say "check the label on the stock".

Ingredients not listed contain none of these. Names must match app/data/ingredients.py;
a test checks that, so a typo can't quietly switch a flag off.

Not allergen-certified. It's a careful household guide, and the app says so.
"""

from enum import StrEnum


class Contains(StrEnum):
    MEAT = "meat"
    SEAFOOD = "seafood"
    DAIRY = "dairy"
    EGG = "egg"
    GLUTEN = "gluten"
    ANIMAL = "animal"  # from an animal but not meat, dairy or egg: honey, gelatine


class Diet(StrEnum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"


M, S, D, E, G, A = (
    Contains.MEAT,
    Contains.SEAFOOD,
    Contains.DAIRY,
    Contains.EGG,
    Contains.GLUTEN,
    Contains.ANIMAL,
)

# What each Diet can't have.
DIET_EXCLUDES: dict[Diet, frozenset[Contains]] = {
    Diet.VEGETARIAN: frozenset({M, S}),
    Diet.VEGAN: frozenset({M, S, D, E, A}),
    Diet.GLUTEN_FREE: frozenset({G}),
    Diet.DAIRY_FREE: frozenset({D}),  # eggs aren't dairy, even though they sit in that aisle
}

_MEAT = (
    "chicken thigh, chicken breast, beef mince, pork mince, lamb chops, beef steak, bacon, "
    "beef chuck steak, chicken drumsticks, chicken wings, chicken mince, whole chicken, "
    "lamb leg, lamb shoulder, lamb mince, pork loin, pork shoulder, veal shanks, ham, "
    "sausages, chorizo, chicken stock, beef stock, pork ribs"
)
_SEAFOOD = (
    "salmon fillet, prawns, canned tuna, white fish fillets, cooked prawns, fish sauce, "
    "oyster sauce, dashi stock, worcestershire sauce, squid"  # worcestershire: anchovies
)
_DAIRY = (
    "milk, butter, cheddar cheese, parmesan, mozzarella, feta, greek yoghurt, "
    "thickened cream, sour cream, ricotta, cream cheese, mascarpone, halloumi, paneer, "
    "gruyere, blue cheese, basil pesto"
)
_EGG = "eggs, egg noodles, mayonnaise, sponge finger biscuits"
# In Australia oats can't be sold as gluten free, so rolled oats and granola count.
_GLUTEN = (
    "plain flour, self-raising flour, soy sauce, pasta, rolled oats, couscous, "
    "pearl barley, bulgur, breadcrumbs, panko breadcrumbs, lasagne sheets, "
    "cannelloni tubes, egg noodles, hokkien noodles, udon noodles, bread, tortillas, "
    "baguette, bread rolls, burger buns, english muffins, pita bread, dumpling wrappers, "
    "filo pastry, puff pastry, shortcrust pastry, potato gnocchi, sponge finger biscuits, "
    "granola, kecap manis, gochujang, chilli bean paste"
)
_ANIMAL = "honey"


def _names(text: str) -> list[str]:
    return [n.strip() for n in text.split(",")]


def _invert(groups: dict[Contains, str]) -> dict[str, frozenset[Contains]]:
    out: dict[str, set[Contains]] = {}
    for flag, text in groups.items():
        for name in _names(text):
            out.setdefault(name, set()).add(flag)
    return {name: frozenset(flags) for name, flags in out.items()}


CONTAINS: dict[str, frozenset[Contains]] = _invert(
    {M: _MEAT, S: _SEAFOOD, D: _DAIRY, E: _EGG, G: _GLUTEN, A: _ANIMAL}
)

# Varies by brand.
CHECK_LABEL: dict[str, frozenset[Contains]] = _invert(
    {
        # Some "vegetable" stock cubes use meat fat. Parmesan and gruyere are
        # traditionally made with animal rennet (not vegetarian); pesto has parmesan.
        M: "stock cubes, vegetable stock, parmesan, gruyere, basil pesto",
        S: "kimchi, green curry paste, red curry paste, laksa paste, tom yum paste",
        D: "dark chocolate, chocolate chips, puff pastry, shortcrust pastry",
        E: "lasagne sheets, pasta",
        G: (
            "stock cubes, chicken stock, beef stock, vegetable stock, sausages, chorizo, "
            "ham, worcestershire sauce, oyster sauce, hoisin sauce, miso paste, "
            "barbecue sauce, cornflour, baking powder, icing sugar, curry powder, "
            "chocolate chips, corn chips, madras curry paste, rogan josh curry paste, "
            "biryani curry paste, tandoori paste, tomato sauce, taco seasoning, taco shells"
        ),
    }
)
