# 2. Recipe sources: our own Seed Recipes + Household favourites; the agent never invents recipes

Date: 2026-11-08 · Status: Accepted · Revised 2026-11-14 (seed source, see below)

## Context

The Recipe Knowledge Base is the pillar that doesn't fill itself from user activity. It needs a seed corpus big enough to learn real RAG on, and a way for Households to add their own recipes. The product is meant to be a real consumer app, so dataset licences matter.

- **RecipeNLG** (~2M recipes): its terms restrict use to *non-commercial research and educational purposes*. Rejected for the product.
- **Food.com recipes + interactions** (~230k recipes, ~1M ratings): licence not confirmed. Its rating data is ideal for a collaborative-filtering experiment.
- A Kaggle recipe dataset mirrored on Hugging Face (`Hieu-Pham/kaggle_food_recipes`, ~13k recipes) is labelled **CC BY-SA 3.0**, which allows commercial use with attribution. ⚠️ Verify the original source and licence before ingesting.

## Decision

1. **Seed Recipes** are ~200 original recipes written for Sweep (Australian names, metric), stored with licence "Sweep original" on every row. *(Revised 2026-11-14, see below.)*
2. Licence-unclear or non-commercial datasets (Food.com, RecipeNLG) are used **only in offline experiments** (`experiments/`), never shipped in the app's Recipe Knowledge Base.
3. **Imported Recipes** are a Household's own favourites, brought in by pasting text, a photo, a link, or typing. *(Revised 2026-11-14, see below.)*
4. **Grounding rule:** the agent may only recommend recipes that exist in the Recipe Knowledge Base, or **Recipe Adaptations** linked to one. Validation rejects any Planned Meal without a real recipe id.

## Consequences

- The seed corpus is smaller than RecipeNLG would give us, so hybrid search and re-ranking are measured on a modest corpus. That's still enough for evaluation.
- The seed data is US/UK-centric (cups, US ingredient names), so ingredient normalisation must handle conversion to metric and AU names.
- Imported pages are **untrusted input** (prompt injection risk, see the security section of the plan).

## Revision (2026-11-14): we write our own Seed Recipes

Checking the CC BY-SA candidate before slice 4: its recipe slugs include chef names and
match Epicurious pages, so it looks scraped, and the "CC BY-SA" label on the mirror
probably isn't the original publisher's to give. A licence is only as good as the
person granting it. So:

- The seed is ~200 recipes drafted with Claude and checked by the product owner, in
  `services/api/app/data/recipes/*.toml`. We own them, so the full method is shown.
- That 13k set may still be used in `experiments/` for retrieval evals, never shipped.
- Trade-off: a smaller corpus (~200 vs 13k). Fine for the MVP and for learning RAG;
  retrieval quality is measured on it in slice 9. Imported Recipes grow it per Household.
- Bonus: the lines are written the way the app needs (AU names, metric), and a test
  makes sure every line parses with plain rules, so loading the seed needs no LLM.

## Revision (2026-11-14): the library is the product; imports are for favourites

Sweep's promise is "you don't have to search for recipes". URL import asks people to go
searching on other sites, so it can't be the main way recipes arrive. Also, the two
sites the product owner suggested don't allow it: RecipeTin Eats blocks Anthropic's
crawlers, and taste.com.au prohibits automated collection without written permission.

- **The Seed library grows on purpose**, to about 500 recipes for launch: Claude drafts,
  automated checks run (every line parses, every ingredient used in the method is listed,
  meat has a safe cooking step), an LLM reviewer flags problems, and a person approves
  the flagged ones. What to write next comes from **gap logs**: searches and agent
  requests that found no good match. Recipes are never generated live for a user.
- **Recipe Adaptations** stretch each recipe ("make it vegetarian", "for two").
- **Favourites** come in through one pipeline with several front doors. Each door only
  gets the text; parsing and the review screen are shared:
  1. "What do you usually cook?" at onboarding matches the meals people name to existing
     recipes, optionally with an Adaptation. No new recipe needed.
  2. Paste recipe text from anywhere. Sweep fetches nothing.
  3. A photo (cookbook page, handwritten card, screenshot), read by Claude.
  4. A link, only where the site's robots.txt allows Sweep's own user agent; otherwise
     the Member is asked to paste the text instead.
  5. Typing it in.
- Every door ends at a **review screen** where AI-matched lines are marked and can be
  corrected before saving.
- Imported Recipes are **private to their Household**, never added to the shared library
  or shown to others. That's what makes keeping a pasted or photographed method
  reasonable: it's a personal copy. Link imports store the facts plus a link back, not
  the method or photos.
- All imported text and images are untrusted data, never instructions.


## Revision (2026-11-14): how the library grew to 500 (slice 4c)

- **Drafting happened in a Claude Code session**, not through the API, so the 303 new
  recipes cost nothing extra. The product owner chose this over a paid drafting script.
- **Automatic checks gate every recipe in CI** (`app/services/recipe_checks.py`): every
  line parses to an Ingredient; the method uses nothing unlisted; raw meat and seafood
  have a cooking step with a time or doneness cue; no step is longer than the stated
  total time (chilling counts); no duplicate titles or near-identical ingredient lists;
  no "vegetarian"/"vegan" claim that an ingredient contradicts (curry pastes, fish sauce,
  dashi count); no odd "X-free" phrases. Running them on the first 197 found real bugs:
  three desserts said "ready in 25 min" but chill for hours, recipes seasoned with salt
  they didn't list, and two used cooked chicken with no step to cook it.
- **The LLM reviewer exists but is opt-in.** It's measured against labelled recipes with
  planted mistakes (`evals/recipe_review.jsonl`) before anyone trusts it.
- **Diet labels in summaries are prose, not rules.** The Dietary Rules check in slice 5
  must work from Ingredients, not from what a summary says.
