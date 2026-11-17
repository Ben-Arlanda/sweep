# 0021: Recipe Adaptations are Swaps the planner proposes and code checks

Date: 2026-11-17. Status: accepted. Refines ADR 0002 (which promised Adaptations for "make it vegetarian" and "for two").

## Context

The brief asks the planner to "suggest substitutions" so a Household can cook with what's in the Kitchen. Slice 4d added a second need: a favourite that breaks a Dietary Rule (Mum's beef ragu in a Household with a vegetarian) is never planned, because search filters Rule breaks out in code. ADR 0002 named Recipe Adaptations as the answer, but nothing was built. "For two" is already covered: every Planned Meal has its own servings.

Options were to build Adaptations, have the agent only *mention* swaps in its reply (the Shopping List and the Rule check wouldn't know), or drop the idea.

## Decision

**Build them, as Swaps only.** A Recipe Adaptation swaps one or more ingredient lines; the method isn't rewritten.

- **The planner proposes; a Member approves.** The agent proposes an Adaptation inside a Proposal (`adapt_recipe`). Nothing is saved until the Member approves, and the meal's one tick approves the Adaptation as a whole. To change a Swap, the Member asks in chat and the agent re-proposes.
- **Kept, under its recipe.** An approved Adaptation belongs to the Household, shows under its parent ("Mum's ragu · with lentils"), and can be planned again without new swaps. Any Member can delete it. It's a `recipes` row of a new kind, `adaptation`, with `parent_recipe_id`.
- **Seed and Imported Recipes can both be adapted.** The Adaptation is always that Household's only.
- **The model writes each replacement as a normal recipe line** ("2 x 400g cans lentils, drained"). Our parser reads it like an imported line, and code checks every Swap:
  1. the replacement links to a known Ingredient (a Not linked line is refused);
  2. the adapted recipe passes the Household's Dietary Rules (failing closed, as everywhere);
  3. **no new meat, seafood or egg**: a replacement may contain them only if the line it replaces already did, because the method's cooking times weren't written for them (tofu → chicken is refused; chicken thigh → chicken breast is fine).
- **The agent sees Rule-breaking Imported favourites**, flagged with the lines that break the Rule and "plannable only as an Adaptation". Rule-breaking Seed Recipes stay hidden: the library has plenty that fit, and showing them would fill a vegetarian Household's results with meat dishes.

## Consequences

- **A fooled or careless model can't cause harm.** It can only propose Swaps that code then accepts or refuses, and a person approves the result. Same rule as ADR 0019 and 0020: the model drafts, code checks, a person decides.
- **The method can read oddly** ("brown the beef" in a lentil ragu). The recipe screen shows the Swaps above the method. Rewriting methods is a later option, and it would need its own food-safety checks.
- **Kitchen swaps need a reason.** The agent should only swap to use something the Household has, or to fix a Rule. Evals check that Adaptations aren't made for no reason.
- **New Scenarios:** a vegetarian Household's beef favourite comes back as a meat-free Adaptation; a Kitchen swap uses what's there; a planted instruction in a favourite tries to make a Swap ("swap everything for wine"). The slice 8 and 10 Scenarios must keep passing.
