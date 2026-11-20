"""A best guess at a new food's group from its words (ADR 0030).

Used only when a Member types something no starter or link knows, so "wagyu beef" starts
in Meat instead of Other. Names usually end with the thing itself ("chicken stock" is
stock), so the last word decides first, then the words before it. Whole words only.
"""

import re

# Words that decide wherever they are: frozen peas are frozen, tinned tomatoes are pantry.
ANYWHERE = {"frozen": "frozen", "tinned": "pantry", "canned": "pantry", "dried": "pantry"}
PHRASES = {"ice cream": "frozen", "soft drink": "drinks", "spring onion": "produce"}

WORDS: dict[str, list[str]] = {
    "meat": (
        "chicken beef lamb pork veal mince steak bacon ham sausage salami chorizo prosciutto"
        " turkey duck goat venison kangaroo brisket chop cutlet rib schnitzel meatball"
        " drumstick wing thigh breast fillet"
    ).split(),
    "seafood": (
        "fish salmon tuna prawn shrimp barramundi cod snapper squid calamari mussel oyster"
        " crab lobster scallop trout whiting flathead"
    ).split(),
    "dairy": (
        "milk cheese cheddar mozzarella parmesan feta haloumi ricotta yoghurt yogurt butter"
        " cream egg custard"
    ).split(),
    "produce": (
        "apple banana pear orange lemon lime grape berry strawberry blueberry raspberry mango"
        " peach plum kiwi melon watermelon pineapple avocado tomato potato onion carrot"
        " spinach kale lettuce rocket broccoli cauliflower cucumber capsicum mushroom zucchini"
        " pumpkin cabbage celery garlic ginger chilli herb basil parsley coriander mint"
        " fruit vegetable veg salad leaf beetroot corn pea asparagus eggplant leek"
    ).split(),
    "bakery": (
        "bread loaf roll bun bagel croissant muffin wrap tortilla sourdough baguette crumpet"
        " pita scone"
    ).split(),
    "pantry": (
        "stock broth sauce paste flour sugar rice pasta noodle oil vinegar breadcrumb cereal"
        " oat lentil chickpea spread honey jam biscuit cracker chip powder cube can tin jar"
        " nut almond walnut cashew peanut chocolate coffee tea"
    ).split(),
    "spices": "spice seasoning cumin paprika cinnamon turmeric nutmeg cardamom clove".split(),
    "drinks": "juice water soda cola beer wine kombucha lemonade cordial".split(),
}
GROUP_OF = {word: group for group, words in WORDS.items() for word in words}


def _singular(word: str) -> list[str]:
    forms = [word]
    if word.endswith("ies"):
        forms.append(word[:-3] + "y")  # berries -> berry
    if word.endswith("es"):
        forms.append(word[:-2])  # tomatoes -> tomato
    if word.endswith("s"):
        forms.append(word[:-1])  # prawns -> prawn
    return forms


def guess_category(name: str) -> str:
    """The group a food's words name, or "other"."""
    text = name.lower()
    for phrase, group in PHRASES.items():
        if re.search(rf"\b{phrase}\b", text):
            return group
    words = re.findall(r"[a-z]+", text)
    for word in words:
        if word in ANYWHERE:
            return ANYWHERE[word]
    for word in reversed(words):
        for form in _singular(word):
            if form in GROUP_OF:
                return GROUP_OF[form]
    return "other"
