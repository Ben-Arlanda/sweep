# 0030: Plain meats are starters, and a new food starts in the group its words name

Date: 2026-11-20. Status: accepted. Builds on ADR 0012 (one matcher, Household Ingredients) and ADR 0024 (Kitchen categories, which the Shopping List groups by).

## Context

The product owner typed "Chicken", "Beef", "Lamb" and "Mince beef" on the Shopping List and they landed under Other. The starters only had cuts ("chicken thigh", "beef mince"), so the matcher found nothing and made a Household Ingredient, which was always category "other". Anything a Member types that Sweep doesn't know ("wagyu beef", "king prawns") had the same problem.

## Decision

1. **Plain "chicken", "beef", "lamb" and "pork" are starters** in Meat, for a list line that doesn't name a cut. "Mince beef", "mince lamb" and "mince pork" are aliases of the mince starters. We don't alias "chicken" to a cut: buying a whole chicken would put chicken thighs in the Kitchen.
2. **A new Household Ingredient starts in the group its words name** (`app/data/food_groups.py`), else Other. The last word decides first, since names end with the thing itself ("chicken stock" is pantry). A few words decide wherever they are ("frozen peas", "tinned tomatoes"). Whole words only.
3. **A one-off migration** moves existing Household Ingredients still in Other to their guessed group.
4. In a recipe method, plain "the beef" means whichever cut the ingredients list, so the unlisted check treats the plain meats as vague words.

## Consequences

- Rules in code, no model: fast, free, testable, and a wrong guess only puts an item under the wrong heading.
- The word list is small and will miss things; anything it misses still goes to Other, as before.
