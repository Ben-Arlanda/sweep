"""Automatic checks for Seed Recipes (slice 4c, ADR 0002).

Plain code, no LLM and no database: fast, free and the same answer every time, so they
can run in CI on every recipe. They catch mistakes that have a clear rule. Judgement
calls ("is this sauce too thin?") are left to the reviewer in `recipe_review`.

1. unparsed:   an ingredient line that matches no Ingredient (we can't shop for it).
2. unlisted:   the method uses an Ingredient the list doesn't have.
3. raw_meat:   raw meat or seafood with no cooking step that has a time or a doneness cue.
4. timing:     one step takes longer than the whole recipe says it does.
5. duplicate:  the same title, or nearly the same ingredients in the same cuisine.
6. diet_claim: the summary says vegetarian or vegan, but an ingredient isn't. A hedged
               note ("vegetarian if the paste is") is fine: it's honest.
7. odd_phrase: "X-free <noun>" where X isn't a diet word ("orange-free greens"). A slip
               the drafting model is prone to; real text says gluten-free, dairy-free...

The Cookable Method checks (slice 4e, CONTEXT.md):

8. unused:     a listed ingredient no step names ("toss everything" names nothing).
9. no_heat:    a pan step before any heat level is given, or baking with no oven temperature.
10. no_time:   a cooking step with no time and no doneness cue.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.data.ingredients import INGREDIENTS
from app.data.recipes import SeedRecipe
from app.services.ingredient_lines import IngredientIndex, ParsedLine, parse_line
from app.services.ingredients import normalise, variants

INDEX = IngredientIndex.from_seed(INGREDIENTS)
CATEGORY = {i.name: i.category for i in INGREDIENTS}
_ALIASES = {i.name: i.aliases for i in INGREDIENTS}


@dataclass(frozen=True)
class Problem:
    slug: str
    check: str
    message: str


# --- unlisted: every name and alias, longest first, so "rice noodles" isn't "rice" ------

# Aliases too vague to point at one Ingredient when they turn up in a method: "cheese"
# could be any cheese, "pepper" could be black pepper or capsicum.
VAGUE = {"cheese", "pepper", "mince", "steak", "cream", "rolls", "wraps", "stock cube"}
VAGUE |= {"cloves", "ice cream", "berries", "fennel"}  # "garlic cloves", "fennel seeds"
# "apple juices bubble", "very long beans", "the chicken pieces", the Spanish tortilla (an omelette)
VAGUE |= {"apple juice", "cherry juice", "long beans", "chicken pieces", "pork strips", "chutney"}
VAGUE |= {"tortilla"}

_VAGUE_FORMS = {form for term in VAGUE for form in variants(term)}  # "roll", "wrap" too

_TERMS: dict[str, str] = {}
for _seed in INGREDIENTS:
    for _term in (_seed.name, *_seed.aliases):
        for _form in variants(normalise(_term)):
            if _form not in _VAGUE_FORMS:
                _TERMS.setdefault(_form, _seed.name)
_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(_TERMS, key=len, reverse=True)) + r")\b"
)


def _mentioned(text: str) -> list[str]:
    """Terms for Ingredients in `text`, longest match first, never overlapping.

    "walnut-sized balls" is a size, not walnuts, so a term right before "-size" is skipped;
    so are "breast-side up", "a potato masher" and "resembles coarse breadcrumbs".
    """
    text = _SIMILE.sub(" ", normalise(text))
    return [m[1] for m in _TERM_PATTERN.finditer(text) if not _NOT_FOOD.match(text, m.end())]


_NOT_FOOD = re.compile(r"-size|-side|\s+masher")
_SIMILE = re.compile(r"\bresembles? (?:\w+ ){0,2}breadcrumbs")
# A general word the method uses for a listed Ingredient: "the pasta sheets" when the
# list has lasagne sheets, "the tomato sauce" made from the listed passata.
UMBRELLA: dict[str, set[str]] = {
    "pasta": {"lasagne sheets", "cannelloni tubes"},
    "tomato sauce": {"passata", "canned tomatoes", "tomatoes"},
    "canned tomatoes": {"tomatoes"},
    "tomato salsa": {"tomatoes", "canned tomatoes", "tomatillos"},
    "corn chips": {"corn tortillas", "tortillas"},
}


# --- raw_meat ----------------------------------------------------------------------

READY_TO_EAT = {"ham", "canned tuna", "cooked prawns", "tofu", "silken tofu", "tofu puffs"}
READY_TO_EAT |= {"sliced turkey", "smoked salmon", "prosciutto", "bresaola", "barbecue chicken"}
READY_TO_EAT |= {"smoked sausage"}  # kransky and kielbasa are sold cooked
COOKING = re.compile(
    r"\b(cook|fry|fried|frying|roast|bake|grill|griddle|barbecue|bbq|simmer|braise|stew|"
    r"poach|steam|sear|brown|boil|stir-fry|stir-fried|char|sizzle|toast)\w*",
)
DONE = re.compile(
    r"\b\d+[½¼¾]?(?:[-–]\d+)?\s*(?:minutes?|mins?|hours?|hrs?)\b|cooked through|no longer pink|"
    r"until pink|turns? pink|"
    r"until (?:done|golden|browned|charred|opaque|tender|crisp|cooked)|°c|juices run clear|"
    # A time in words: "for two minutes", "a few minutes" (slice 4g's longer writing).
    r"\b(?:one|two|three|four|five|six|eight|ten|fifteen|twenty|thirty|a|a few|a couple of|"
    r"several)\s+(?:more\s+)?(?:minutes?|mins?|hours?)\b",
)


def _needs_cooking(names: set[str]) -> list[str]:
    return sorted(
        n for n in names if CATEGORY.get(n) in {"meat", "seafood"} and n not in READY_TO_EAT
    )


def _cooked(method: Sequence[str]) -> bool:
    return any(COOKING.search(s.lower()) and DONE.search(s.lower()) for s in method)


# --- diet_claim ------------------------------------------------------------------

# Not meat to look at, but usually made with fish, shrimp or meat stock.
HIDDEN_ANIMAL = {
    "fish sauce",
    "oyster sauce",
    "worcestershire sauce",
    "dashi stock",
    "kimchi",
    "chicken stock",
    "beef stock",
    "stock cubes",
    "green curry paste",
    "red curry paste",
    "laksa paste",
    "tom yum paste",
}
NOT_VEGAN = {"eggs", "honey"}
_PLANT_PROTEIN = {"tofu", "silken tofu", "tofu puffs"}  # filed under "meat" in the aisle
_CLAIM = re.compile(r"\b(vegan|vegetarian)\b", re.IGNORECASE)
_HEDGE = re.compile(r"\b(if|check|without)\b", re.IGNORECASE)


def _diet_problem(summary: str, names: set[str]) -> str | None:
    # Only plain claims count. "Vegetarian if the paste is", "check the label if you're
    # vegetarian" and "vegan without the parmesan" are honest, so they're fine.
    sentences = re.split(r"(?<=[.!?;])\s+", summary)
    claims = {m.lower() for s in sentences if not _HEDGE.search(s) for m in _CLAIM.findall(s)}
    if not claims:
        return None
    meat = {n for n in names if CATEGORY.get(n) in {"meat", "seafood"}} - _PLANT_PROTEIN
    not_vegetarian = sorted(meat | (names & HIDDEN_ANIMAL))
    if not_vegetarian:
        claim = "vegan" if "vegan" in claims else "vegetarian"
        return f"says {claim} but has {', '.join(not_vegetarian)}"
    if "vegan" in claims:
        animal = sorted({n for n in names if CATEGORY.get(n) == "dairy"} | (names & NOT_VEGAN))
        if animal:
            return f"says vegan but has {', '.join(animal)}"
    return None


# --- odd_phrase --------------------------------------------------------------------

_ODD_FREE = re.compile(r"\b(?!(?:gluten|dairy|meat|sugar|nut|egg|fat|salt-reduced)-)(\w+)-free \w+")


def _odd_phrases(r: SeedRecipe) -> list[str]:
    text = " ".join([r.title, r.summary, *r.ingredients, *r.method])
    return [m.group(0) for m in _ODD_FREE.finditer(text)]


# --- timing ------------------------------------------------------------------------

_DURATION = re.compile(r"(\d+)([½¼¾]?)(?:\s*[-–]\s*(\d+))?\s*(hours?|hrs?|minutes?|mins?)\b")
_HALF = {"": 0.0, "½": 0.5, "¼": 0.25, "¾": 0.75}


def _longest_step(method: Sequence[str]) -> int:
    longest = 0
    for step in method:
        total = 0
        for low, part, high, unit in _DURATION.findall(step.lower()):
            amount = int(high) if high else int(low) + _HALF[part]  # "1½ hours" = 1.5
            total += round(amount * 60 if unit.startswith("h") else amount)
        longest = max(longest, total)
    return longest


# --- duplicate ---------------------------------------------------------------------


def _similar(a: set[str], b: set[str]) -> bool:
    """Nearly the same shopping: 85% of the combined ingredients are shared."""
    return bool(a and b) and len(a & b) / len(a | b) >= 0.85


# --- Cookable Method: unused, no_heat, no_time ----------------------------------------

# Words in a line that say nothing about which ingredient it is.
_FILLER = {
    "red", "green", "white", "brown", "black", "fresh", "large", "small", "medium", "finely",
    "dried", "ground", "can", "cans", "tin", "whole", "plain", "extra", "light", "dark",
    "sweet", "baby", "tbsp", "tsp", "cup", "cups", "packet", "sheets", "bunch", "handful",
    "pinch", "grated", "sliced", "chopped", "diced", "sprigs", "cloves", "slices", "stick",
    "sticks", "and", "the", "for", "with",
}  # fmt: skip
_HERBS = {
    "coriander", "parsley", "basil", "mint", "dill", "rosemary", "thyme", "chives", "oregano",
    "sage", "tarragon", "bay leaves", "dried oregano", "dried sage", "thai basil",
}  # fmt: skip
_SALAD = {
    "lettuce", "rocket", "baby spinach", "tomatoes", "cherry tomatoes", "cucumber", "red onion",
    "capsicum", "avocado", "radishes", "mixed salad leaves",
}  # fmt: skip
_DRY = {
    "plain flour", "self-raising flour", "baking powder", "bicarbonate soda", "cocoa powder",
    "white sugar", "caster sugar", "brown sugar", "icing sugar", "salt", "rolled oats",
    "ground cinnamon", "desiccated coconut", "cornflour", "almond meal",
}  # fmt: skip
_WET = {"milk", "eggs", "butter", "vegetable oil", "greek yoghurt", "honey", "vanilla extract"}
# A word a method uses for several ingredients at once ("add the spices").
_GROUPS: dict[str, set[str]] = {
    "spice": {i.name for i in INGREDIENTS if i.category == "spices"},
    "herb": _HERBS,
    "cheese": {i.name for i in INGREDIENTS if "cheese" in i.name}
    | {"parmesan", "mozzarella", "feta", "ricotta", "halloumi", "gruyere", "paneer"}
    | {"queso fresco", "pecorino"},
    "season": {"salt", "black pepper"},
    "salad": _SALAD,
    "veg": {i.name for i in INGREDIENTS if i.category == "produce"} - _HERBS,
    "vegetable": {i.name for i in INGREDIENTS if i.category == "produce"} - _HERBS,
    "dry ingredient": _DRY,
    "wet ingredient": _WET,
}
_EGG_PARTS = re.compile(r"\b(?:yolks?|whites?)\b")


def _used(text: str, name: str, method: str) -> bool:
    forms = {f for t in (name, *_ALIASES.get(name, ())) for f in variants(normalise(t))}
    head = normalise(re.split(r"[,(]", text)[0])
    words = {w for w in re.findall(r"[a-z-]+", head) if len(w) >= 3 and w not in _FILLER}
    forms |= {f for w in words for f in variants(w)}
    forms |= {g for g, members in _GROUPS.items() if name in members}
    forms |= {u for u, members in UMBRELLA.items() if name in members}  # "the pasta sheets"
    if name == "eggs" and _EGG_PARTS.search(method):
        return True
    return any(re.search(rf"\b{re.escape(f)}(?:s|ed)?\b", method) for f in forms)  # "salted"


_CLAUSE = r"(?:^|[.;,]\s*|\b(?:then|and|or)\s+)(?:gently\s+|quickly\s+)?(?:shallow-|deep-|pan-)?"
# "brown sugar" and "brown onion" are things, not a step.
_BROWN = r"brown(?!\s+(?:sugar|rice|onions?|bread|lentils|mushrooms))"
_PAN = re.compile(
    _CLAUSE + rf"(fry|sear|{_BROWN}|sauté|saute|stir-fry|soften|scramble|cook)\b"
    r"|\btoast\b[^.]*\bdry (?:frying )?pan"
)
# "Heat" isn't here: heating a pan or oven is set-up, needing a heat level, not a time.
_COOK = re.compile(
    # "BBQ sauce" and "a grill pan" are things, not a step.
    _CLAUSE + r"(cook|fry|roast|bake|grill(?! pan)|griddle|(?:barbecue|bbq)(?! sauce)|simmer|"
    r"braise|stew|poach|"
    rf"steam|sear|{_BROWN}|boil|stir-fry|char|toast|soften|scramble)\b"
)
_OVEN = re.compile(_CLAUSE + r"(bake|roast)\b")
_HEAT = re.compile(
    r"\b(?:low|medium|high|medium-high|medium-low|gentle|moderate)\b(?:[- ]\w+)? heat|"
    r"\bhot (?:\w+ )?(?:pan|wok|frying pan|oil|grill|barbecue|griddle|plate)|"
    r"\bvery hot\b|\bsmoking\b|"
    r"°c|\btoaster\b|\bgrill\b|\buntil (?:very )?hot\b|\bgently\b"
)
# Simmering or boiling says how hot this step is, but not the next one: boiling the pasta
# doesn't say how hot to fry the garlic.
_OWN_HEAT = re.compile(r"\bsimmer|\bboil")
_OVEN_TEMP = re.compile(r"\boven\b[^.]*?°c")
# What a cook can see, feel or smell when a step is done.
_CUE_WORDS = (
    *("golden", "brown", "browned", "charred", "opaque", "tender", "crisp", "crispy", "cooked"),
    *("translucent", "al dente", "absorbed", "evaporat\\w*", "soft\\w*", "thick\\w*", "reduc\\w*"),
    *("wilted", "melted", "bubbl\\w*", "hot", "fluffy", "puffed", "caramelis\\w*", "smooth"),
    *("colou?r\\w*", "fragrant", "clear", "blister\\w*", "collaps\\w*", "break down"),
    *("float", "risen", "skewer", "doneness", "firm", "set", "syrupy", "coats?", "render\\w*"),
    *("pink", "no raw", "dissolv\\w*", "glossy", "sticky", "darken\\w*", "spotted", "done"),
    *("pierced", "slides?", "jammy", "lift\\w*", "blacken\\w*", "moisture", "releases?"),
)
_CUE = re.compile(
    DONE.pattern + r"|packet|seconds?\b|heat(?:ed)? through|"
    r"until (?:just )?(?:fragrant|soft|softened|wilted|set|melted|thick|thickened|bubbling|"
    r"hot|heated|warmed|fluffy|puffed|reduced|"
    r"caramelised|smoking|deep golden|steaming|smooth|coloured|it colours|the garlic just)|"
    # A few words can come between: "until the onion is translucent", "until lightly golden".
    r"\buntil\b[^.;:]{0,50}?\b(?:" + "|".join(_CUE_WORDS) + r")\b|preferred doneness|to your liking"
)
# A staple cooked by its packet needs no heat or time of its own: "Cook the rice according
# to the packet." A bare "Cook the rice." still needs one (the product owner's call).
_STAPLE = re.compile(
    r"\b(?:meanwhile,? )?cook (?:the )?(?:(?:rice|pasta|noodles|spaghetti|linguine|penne|"
    r"couscous|quinoa|soba|udon|rice noodles|egg noodles|gnocchi|vermicelli|oven chips) )?"
    r"(?:according to|following) (?:the )?packet(?: instructions| directions)?"
)


def _short(step: str) -> str:
    words = step.split()
    return step if len(words) <= 9 else " ".join(words[:9]) + "…"


def _method_problems(r: SeedRecipe, lines: Sequence[ParsedLine]) -> list[Problem]:
    problems: list[Problem] = []
    method = normalise(" ".join(r.method))
    for line in lines:
        if line.ingredient and not _used(line.raw_text, line.ingredient.name, method):
            problems.append(Problem(r.slug, "unused", f"'{line.raw_text}' isn't used in any step"))

    oven_temp = any("°c" in s.lower() for s in r.method)
    heat = False
    for step in r.method:
        low = _STAPLE.sub("", step.lower())
        # The oven's temperature says nothing about how hot the pan should be.
        heat = heat or bool(_HEAT.search(_OVEN_TEMP.sub("", low)))
        if _PAN.search(low) and not (heat or _OWN_HEAT.search(low)):
            problems.append(Problem(r.slug, "no_heat", f"'{_short(step)}' gives no heat level"))
            heat = True  # one report per method is enough to fix it
        if _OVEN.search(low) and not oven_temp:
            problems.append(
                Problem(r.slug, "no_heat", f"'{_short(step)}' gives no oven temperature")
            )
        if _COOK.search(low) and not _CUE.search(low):
            problems.append(
                Problem(r.slug, "no_time", f"'{_short(step)}' gives no time or doneness cue")
            )
    return problems


def check_recipes(recipes: Sequence[SeedRecipe]) -> list[Problem]:
    problems: list[Problem] = []
    listed: dict[str, set[str]] = {}

    for r in recipes:
        lines = [parse_line(text, INDEX) for text in r.ingredients]
        names = {line.ingredient.name for line in lines if line.ingredient}
        listed[r.slug] = names
        problems += [
            Problem(r.slug, "unparsed", f"'{line.raw_text}' matches no Ingredient")
            for line in lines
            if line.needs_review
        ]

        # A term is fine if it's a listed Ingredient, or a word inside a listed line
        # ("the rice" when the list says "arborio rice", "the onion" for "red onion").
        written = " ".join(normalise(text) for text in r.ingredients)
        reported: set[str] = set()
        for term in _mentioned(" ".join(r.method)):
            name = _TERMS[term]
            in_lines = any(re.search(rf"\b{re.escape(f)}\b", written) for f in variants(term))
            covered = bool(UMBRELLA.get(name, set()) & names)
            if name in names or name in reported or in_lines or covered:
                continue
            reported.add(name)
            problems.append(
                Problem(
                    r.slug, "unlisted", f"the method uses {name}, which isn't in the ingredients"
                )
            )

        uncooked = {line.ingredient.name for line in lines if line.ingredient and not line.prepared}
        raw = _needs_cooking(uncooked)
        if raw and not _cooked(r.method):
            problems.append(
                Problem(
                    r.slug,
                    "raw_meat",
                    f"{', '.join(raw)} needs a cooking step with a time or a doneness cue",
                )
            )

        problems += _method_problems(r, lines)

        diet = _diet_problem(r.summary, names)
        if diet:
            problems.append(Problem(r.slug, "diet_claim", diet))

        problems += [
            Problem(r.slug, "odd_phrase", f"'{phrase}' reads like a slip")
            for phrase in _odd_phrases(r)
        ]

        longest = _longest_step(r.method)
        if longest > r.minutes:
            problems.append(
                Problem(
                    r.slug,
                    "timing",
                    f"one step takes {longest} min but the recipe says {r.minutes} min in total",
                )
            )

    seen: dict[str, SeedRecipe] = {}
    checked: list[SeedRecipe] = []
    for r in recipes:
        title = normalise(r.title)
        if title in seen:
            problems.append(Problem(r.slug, "duplicate", f"same title as {seen[title].slug}"))
        else:
            twin = next(
                (
                    o
                    for o in checked
                    if o.cuisine == r.cuisine and _similar(listed[o.slug], listed[r.slug])
                ),
                None,
            )
            if twin is not None:
                problems.append(
                    Problem(r.slug, "duplicate", f"nearly the same ingredients as {twin.slug}")
                )
        seen.setdefault(title, r)
        checked.append(r)
    return problems
