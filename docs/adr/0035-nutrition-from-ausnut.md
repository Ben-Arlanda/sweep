# 0035: Nutrition worked out from AUSNUT, per Ingredient

Date: 2026-11-24. Status: accepted. Slice 4h.

## Context

Members want to see what a recipe gives them per serve. Our recipes have no nutrition data, but every line already has an Ingredient and a base amount in g, ml or count (ADR 0032). So we can add up the Ingredients if each one has nutrient values.

## Decision

1. **Source: FSANZ's AUSNUT 2023** (Food nutrient profiles and Food measures; credited "Nutrition data: FSANZ").
   - Its weights ("1 medium onion = 142 g") and densities come from FSANZ too, so no model guesses them.
   - FSANZ's site is CC BY 4.0 unless it says otherwise, and the AUSNUT pages don't. Confirm with FSANZ before launch.
   - Rejected alternatives:
     - AUSNUT 2011–13 (CC BY 3.0): older, and no longer on FSANZ's download page.
     - AFCD: ShareAlike, plus an extra database term.
     - USDA FoodData Central: American foods.
2. **Eight nutrients, the Australian label set:** energy, protein, fat, saturated fat, carbs, sugars, sodium, fibre. Energy is shown as "2,090 kJ (500 Cal)", and % Daily Intake uses Australia's 8,700 kJ reference values. Numbers are rounded to whole units. We don't show vitamins and minerals: estimates from raw Ingredients are poor for them.
3. **Claude matches, code looks up, the product owner reviews.**
   - For each Ingredient, Claude picks an AUSNUT food ID, and an AUSNUT measure for each unit recipes use that has no fixed size ("each", "clove"); densities come from AUSNUT directly (ml Ingredients).
   - Plain code copies the nutrient values from the AUSNUT file. A model never writes a nutrient number.
   - The product owner checks the matches on a review page, and the result is a committed data file.
4. **Worked out by the API from a recipe's lines on each request**, so Seed Recipes, Imported Recipes and Adaptations all get it. It's per serve, so the Serves stepper doesn't change it.
5. **Missing lines:**
   - "To taste" and optional lines are left out.
   - A Household Ingredient or unmatched line is listed under the table as "Doesn't include: …".
   - If a missing line is the main protein, or more than about 15% of the recipe's weight, the page shows "Nutrition isn't available" instead of a misleading number.
6. **Recipe page only for now.** The planner, search and weekly totals don't use it yet.

7. **Rules from checking every Seed Recipe:**
   - Water counts as nothing.
   - Oil for frying counts at 10%, for what the food soaks up. That's an oil line of 200 ml or more, or one that says "for frying"; no recipe eats that much oil.
   - A cooked amount ("4 cups cooked rice") is a missing line, never weighed as raw (about 3× too much). The ingredient parser decides what's cooked, as it does for the Shopping List.

## Consequences

- An estimate, not a lab figure: cooking losses, oil left in the pan and brand differences aren't counted. The page says so.
- A wrong match is the main way it can go wrong, and the review page is where it's caught. New starter Ingredients need a match too, and a test fails when one is missing.
- "Nutrition in planning" (filters like "under 600 Cal", high protein) is a possible later slice. The numbers come from the API, so it can reuse them.
