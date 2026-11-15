# 12. The Kitchen takes anything: Household Ingredients and one matcher

Date: 2026-11-15 · Status: Accepted

## Context

The Shopping List accepts any text, like Apple Reminders. The Kitchen only stores Ingredients (ADR 0003), so it can compare what you have with recipes. With 255 starter Ingredients and strict matching, a Member ticked "Kale" and "Chocolate" and they silently never reached the Kitchen. The product owner wants the list to stay "add anything", **everything ticked to reach the Kitchen (non-food included)**, recipe matching to keep working, and favourite recipes imported later (slice 4d) to match exactly what's in the Kitchen.

## Decision

- **Household Ingredients.** `ingredients.household_id`: NULL for the shared starter set, set for an Ingredient one Household created. Names are unique per owner (`UNIQUE NULLS NOT DISTINCT (household_id, name)`). Household Ingredients have category `other` (so they default to the Cupboard), unit `count`, no density.
- **One matcher for everything**: `ingredients.resolve(household, text, create)`, used by Shopping List items, the Kitchen's "add", the agent, and recipe lines (Imported Recipes in 4d). Lookup order:
  1. the Household's **links** ("chocolate" → dark chocolate)
  2. starter names and aliases (with simple plurals, as now)
  3. the Household's own Ingredients
  4. otherwise create a Household Ingredient (when `create`), so nothing is refused.
  Matching stays strict: no fuzzy guesses. A wrong link would quietly put the wrong thing in the Kitchen; the Member fixes near-misses with a link.
- **Household links** (`household_ingredient_links(household_id, name, ingredient_id)`). Re-linking a list item ("Link to… dark chocolate") saves a link for that name, so future items and imported recipe lines follow it. Re-linking a ticked item still moves its Kitchen stock (existing behaviour).
- **Visibility is scoped everywhere.** Every Ingredient read (search, get by id, list/Kitchen helpers, agent tools) allows starters plus the caller's own Household only. An id from another Household is "not found". Seed Recipes may only use starter Ingredients (recipe checks unchanged).
- **Merging into starters.** When a starter Ingredient is added with the same name as Household ones (e.g. we add "kale"), the seed upsert repoints Kitchen rows, Staples, list items and links to the starter and deletes the Household copies. Households start matching recipes with no action.
- Seed Recipes don't change: their lines resolve without a Household, so they can only use starters.

## Consequences

- Nothing a Member types is refused. Non-food ("bin bags") becomes a Household Ingredient in the Cupboard; remove it from the Kitchen if you don't want it tracked.
- Household Ingredients don't convert units ("1 bunch" stays "some" in the Kitchen unless bought in the same unit).
- Seed Recipes only match Household Ingredients after a merge, so growing the starter list (kale, common greens) still matters. Recipe search by meaning (embeddings) finds recipes that mention an item even with no link.
- Every new query on `ingredients` must apply the visibility rule. A test covers each route that takes an Ingredient id.
