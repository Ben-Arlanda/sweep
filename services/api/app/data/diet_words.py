"""Judging a food Sweep doesn't know by the words in its name (ADR 0032).

Only for Household Ingredients: starters have their contents recorded in data/diet.py.
A name with a word that likely breaks a diet is held back ("andouille sausage"); one for
something that depends on the brand is "check the label" ("satay sauce"); anything else
passes. Worked out when a recipe is checked, so a better list fixes every recipe at once.

Whole words only, plurals ignored. Not allergen-certified: a careful household guide.
"""

import re
from functools import cache

from app.data.diet import Contains

M, S, D, E, G, A = (
    Contains.MEAT,
    Contains.SEAFOOD,
    Contains.DAIRY,
    Contains.EGG,
    Contains.GLUTEN,
    Contains.ANIMAL,
)

# A word here means the food very likely contains it.
LIKELY: dict[str, frozenset[Contains]] = {
    **dict.fromkeys(
        (
            "chicken beef lamb pork veal mince steak bacon ham sausage salami chorizo"
            " prosciutto pancetta turkey duck goat venison kangaroo brisket schnitzel"
            " meatball meat lard andouille kransky kielbasa pepperoni"
        ).split(),
        frozenset({M}),
    ),
    **dict.fromkeys(
        (
            "fish salmon tuna prawn shrimp barramundi cod snapper squid calamari mussel"
            " oyster crab lobster scallop trout anchovy sardine clam octopus"
        ).split(),
        frozenset({S}),
    ),
    **dict.fromkeys(
        (
            "milk cheese cheddar mozzarella parmesan feta haloumi halloumi ricotta yoghurt"
            " yogurt butter buttermilk cream ghee custard mascarpone paneer brie camembert"
        ).split(),
        frozenset({D}),
    ),
    **dict.fromkeys("egg mayonnaise mayo meringue aioli".split(), frozenset({E})),
    **dict.fromkeys(
        (
            "flour bread wheat barley rye spelt pasta noodle spaghetti couscous semolina"
            " breadcrumb panko biscuit cracker cake pastry tortilla wrap bun roll bagel"
            " croissant beer seitan sourdough brioche"
        ).split(),
        frozenset({G}),
    ),
    "cheesecake": frozenset({D, G}),
    **dict.fromkeys("honey gelatine gelatin".split(), frozenset({A})),
}
# A word here means it depends on the brand: the agent says "check the label".
CHECK: dict[str, frozenset[Contains]] = {
    **dict.fromkeys(("stock", "broth", "gravy"), frozenset({M, G})),
    **dict.fromkeys(("sauce", "seasoning", "marinade", "rub"), frozenset({G})),
    "sausage": frozenset({G}),
    "paste": frozenset({S, G}),  # curry pastes: shrimp paste, wheat
    "dressing": frozenset({D, E}),
    "chocolate": frozenset({D}),
}
# Foods that only look risky. Blanked out first, so "peanut butter cheesecake" is still
# cheesecake, but "peanut butter" alone isn't dairy.
SAFE_FOODS = (
    "peanut butter, almond butter, cashew butter, nut butter, cocoa butter, apple butter,"
    " coconut cream, coconut milk, coconut yoghurt, oat milk, almond milk, soy milk,"
    " rice milk, cashew milk, rice noodle, rice paper, rice flour, almond flour,"
    " coconut flour, chickpea flour, corn flour, corn tortilla, oyster mushroom,"
    " cream of tartar, beef tomato, egg free, fish free"
).split(", ")
# Words that say what a food is free of, for the whole name.
QUALIFIERS: dict[str, frozenset[Contains]] = {
    "gluten free": frozenset({G}),
    "dairy free": frozenset({D}),
    "egg free": frozenset({E}),
    "vegetarian": frozenset({M, S}),
    "vegan": frozenset({M, S, D, E, A}),
    "plant based": frozenset({M, S, D, E, A}),
}


def _words(name: str) -> list[str]:
    return re.findall(r"[a-z]+", name.lower().replace("-", " "))


def _singular(word: str) -> set[str]:
    forms = {word}
    if word.endswith("ies"):
        forms.add(word[:-3] + "y")
    if word.endswith("es"):
        forms.add(word[:-2])
    if word.endswith("s"):
        forms.add(word[:-1])
    return forms


def _forms(word: str) -> set[str]:
    """Every simple singular and plural spelling: "berries" → berry, berries, …"""
    out = set()
    for form in _singular(word):
        out |= {form, form + "s", form + "es"}
        if form.endswith("y"):
            out.add(form[:-1] + "ies")
    return out


def _phrase(words: list[str]) -> re.Pattern[str]:
    """Whole words, each singular or plural: "rice noodle" finds "rice noodles"."""
    parts = [
        "(?:" + "|".join(map(re.escape, sorted(_forms(w), key=len, reverse=True))) + ")"
        for w in words
    ]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b")


def _without_safe_foods(text: str) -> str:
    for food in SAFE_FOODS:
        text = _phrase(food.split()).sub(" ", text)
    return text


@cache  # pure, and called for every Ingredient on every search
def judge(name: str) -> tuple[frozenset[Contains], frozenset[Contains]]:
    """(what it likely contains, what to check on the label) for a food's name."""
    text = " ".join(_words(name))
    free: set[Contains] = set()
    for qualifier, flags in QUALIFIERS.items():
        if _phrase(qualifier.split()).search(text):
            free |= flags
    likely: set[Contains] = set()
    check: set[Contains] = set()
    for word in _words(_without_safe_foods(text)):
        for form in _singular(word):
            likely |= LIKELY.get(form, frozenset())
            check |= CHECK.get(form, frozenset())
    return frozenset(likely - free), frozenset(check - likely - free)


@cache
def names_food(name: str, food: str) -> bool:
    """Does `name` contain the excluded `food` ("no mushrooms": "shiitake mushrooms")?
    Whole words, plurals ignored, and never inside a safe food ("coconut milk")."""
    wanted = _words(food)
    if not wanted:
        return False
    text = _without_safe_foods(" ".join(_words(name)))
    return bool(_phrase(wanted).search(text))
