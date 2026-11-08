# 2. Recipe sources: licence-clear seed dataset + URL imports; the agent never invents recipes

Date: 2026-11-08 · Status: Accepted (seed dataset choice pending licence check)

## Context

The Recipe Knowledge Base is the pillar that doesn't fill itself from user activity. It needs a seed corpus big enough to learn real RAG on, and a way for Households to add their own recipes. The product is meant to be a real consumer app, so dataset licences matter.

- **RecipeNLG** (~2M recipes): its terms restrict use to *non-commercial research and educational purposes*. Rejected for the product.
- **Food.com recipes + interactions** (~230k recipes, ~1M ratings): licence not confirmed. Its rating data is ideal for a collaborative-filtering experiment.
- A Kaggle recipe dataset mirrored on Hugging Face (`Hieu-Pham/kaggle_food_recipes`, ~13k recipes) is labelled **CC BY-SA 3.0**, which allows commercial use with attribution. ⚠️ Verify the original source and licence before ingesting.

## Decision

1. **Seed Recipes** come from a dataset whose licence allows our use (current candidate: the CC BY-SA set above), stored with source and licence on every row.
2. Licence-unclear or non-commercial datasets (Food.com, RecipeNLG) are used **only in offline experiments** (`experiments/`), never shipped in the app's Recipe Knowledge Base.
3. **Imported Recipes**: a Member pastes a URL and we read the page's schema.org `Recipe` JSON-LD. We store structured fields, the source URL and attribution, and the original page stays the place to read full instructions.
4. **Grounding rule:** the agent may only recommend recipes that exist in the Recipe Knowledge Base, or **Recipe Adaptations** linked to one. Validation rejects any Planned Meal without a real recipe id.

## Consequences

- The seed corpus is smaller than RecipeNLG would give us, so hybrid search and re-ranking are measured on a modest corpus. That's still enough for evaluation.
- The seed data is US/UK-centric (cups, US ingredient names), so ingredient normalisation must handle conversion to metric and AU names.
- Imported pages are **untrusted input** (prompt injection risk, see the security section of the plan).
