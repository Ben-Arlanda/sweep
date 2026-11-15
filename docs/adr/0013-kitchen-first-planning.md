# 13. Kitchen-first planning: the app ranks, the agent chooses

Date: 2026-11-15 · Status: Accepted

## Context

Sweep's promise is "cook what you've got, buy only what's missing". The agent (ADR 0008) planned the other way round: it searched recipes by meaning from whatever query the model wrote, put them on days, and only then checked the Kitchen (`check_kitchen_coverage`). Nothing made the Kitchen drive the choice, and the `must_use_ingredients` filter matched Ingredient ids only, so a Household Ingredient (ADR 0012) always returned no recipes. The product owner wants "Plan my week" (and a "Just tonight" option) to start from what's in the Kitchen.

## Decision

- **Kitchen Match is deterministic.** A pure function scores each recipe against a snapshot of the Kitchen. Each needed line (not optional) is:
  - **have**: a Staple marked "have", or a Tracked item whose status is Confirmed or Estimated;
  - **maybe**: a Tracked item whose status is Unknown;
  - **missing**: anything else with an Ingredient.
  - A line with no Ingredient ("water", unrecognised) is ignored, unless its text names one of the Household's own Ingredients as a whole word ("finger lime"), which counts as have.
  - Amounts are not compared here; `check_kitchen_coverage` still works out how much to buy.
- **Ranking: fewest things to buy.** Sort by missing count, then maybe count, then the number of Tracked (not Staple) items used, most first, so a recipe that uses what you bought wins a pantry-only one. Ties by title.
- **Recipes that need shopping are allowed**, with what's missing listed. A Kitchen with three things in it should still get a week of dinners.
- **New agent tool `recipes_from_kitchen`** (optional taste `query`, `max_minutes`, `cuisine`, `exclude_recipe_ids`). Dietary Rules filter in SQL as before. With a `query`, search by meaning first (top 60), then re-rank by Kitchen Match: hybrid retrieval with a deterministic re-ranker. The system prompt says plans start from this tool; `search_recipes` is for a specific dish the Member asks for.
- **`must_use_ingredients`** resolves names with the matcher; a Household Ingredient matches recipe lines whose text names it.
- **Entry points:** Home has "Plan my week" and "Just tonight". Each opens a new plan and sends a fixed first message, visible in the chat like one the Member typed.
- **Measured.** An offline eval compares Kitchen-first against search-only on sample Kitchens: average items to buy per meal, and the share of Kitchen items a plan uses. No model calls.

## Consequences

- The model can't plan away from the Kitchen by accident, and "why this recipe?" has a plain answer (you have 7 of 9).
- Scoring runs in Python over every eligible recipe (500 × about 9 lines): milliseconds now. Move it into SQL if the library grows past a few thousand.
- Matching a Household Ingredient by text is a whole-word match on a name the Household chose. It can't put anything in the Kitchen or on the list; it only changes ranking and labels.
- No expiry dates, so "use it up before it goes off" waits until the Kitchen tracks them.
