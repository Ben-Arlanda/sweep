# 0032: Every recipe line has an Ingredient, and new foods are judged by their words

Date: 2026-11-22. Status: accepted. Amends ADR 0020 (unmatched lines stayed "Not linked") and how the Dietary Rules treat foods Sweep doesn't know. Builds on ADR 0012 (Household Ingredients, one matcher, merging into starters) and ADR 0030 (judging a new food by its words).

## Context

On an imported Jambalaya, 7 of 22 lines had no Ingredient, so the recipe screen showed neither "In kitchen" nor "Add to list", and "You have X of Y" left them out. Three causes:

1. The catalogue grew after the import ("onion powder", "sweet paprika" were added that night), and matching only runs once, at import. An unlinked line has nothing for the starter merge to repoint, so it never heals.
2. Nested notes like `(, uncooked (Note 2))` left a stray `)` in the name.
3. Wording the rules didn't know: "celery ribs", "low-sodium chicken broth / stock", "long grain rice", "cayenne powder".

Many households will import recipes with foods Sweep doesn't know, and the product owner expects members to **rarely link lines by hand**. So the system has to resolve them itself, and nothing can rely on a member fixing a near-miss.

Separately, the Dietary Rules failed closed: any line Sweep couldn't check counted as a break, so one unfamiliar spice kept a recipe out of every plan. The product owner wants a recipe held back only when it's likely to break a rule.

## Decision

**Every recipe line has an Ingredient.**

1. Matching runs clean-then-look-up: drop amounts, notes (nested ones too), describing words ("low-sodium", "fresh"), trailing measures ("ribs", "stalks") and "or" alternatives, then look the cleaned name up again. Words removed from the name go into the line's note.
2. A line still unmatched, which is something you shop for, gets a **Household Ingredient** named by that cleaned name (`ingredients.resolve(create=True)`), for the recipe's Household. Only things nobody shops for (water, ice) stay unlinked.
3. The review screen shows such a line as **"New: andouille sausage"** before saving. The server works the name out (one shared function for the preview and the save) and never accepts a name from the client. Save creates it inside the same transaction; the unique `(household_id, name)` constraint means repeats reuse one Ingredient.
4. A line naming two known foods with "and" ("salt and pepper") is saved as two lines, both keeping the original text. Otherwise it takes the normal path.
5. The database enforces it: a recipe line's Ingredient may be empty only for things nobody shops for, and an Ingredient a recipe line uses can't be deleted (the foreign key has no ON DELETE, so Postgres's default NO ACTION; the merge repoints lines first). Not RESTRICT: it checks mid-cascade, so deleting a Household (its recipes and its Ingredients cascade together) could fail depending on order. Seed Recipe lines must all match a starter; the loader refuses the whole load otherwise. The migration stops with a clear message if unlinked lines exist (test data was deleted by hand, not backfilled).
6. The recipe screen shows the note under the name (Cook Mode lists steps only, so it has no line to show it on) ("Andouille sausage · 200 g · or smoked sausage · sliced 0.5 cm thick"). The Shopping List gets the amount and name only.

**Healing and growth: rules only, no AI.**

7. A **gap report** (`python -m app.gap_report`) lists Household Ingredients created from recipes, as names and counts only, for names in at least 3 Households, with how the diet words would judge each. Common ones become starters or aliases, and the existing merge repoints every Household's lines, Kitchen rows and list items.
8. Every real miss becomes a regression test, so matching only gets better.
9. No AI mapping to existing names (as ADR 0020). It can only pick names we have, so when the right one is missing, a "closest" pick can drop a dietary flag: "flour tortillas" → "corn tortillas" would pass gluten free. Revisit only if the gap report shows rules can't keep up, and then only with a check that the pick has at least the line's likely dietary flags, measured by an eval.

**Dietary Rules judge new foods by their words, at check time.**

10. Shared Ingredients keep their recorded contents (`data/diet.py`). A Household Ingredient's name is read for words that likely break a diet ("sausage", "flour", "bread", "cheese", "prawn", "egg"…) → **held back**; for brand-varying foods ("seasoning", "sauce", "paste", "stock") → **check the label** (AI-only, as today); otherwise → **passes**. Exceptions ("peanut butter", "coconut cream", "oat milk", "rice noodles") are listed and tested. Worked out at check time, so a better word list fixes every recipe at once.
11. An excluded food ("no mushrooms") matches any Ingredient whose name contains it as a whole word, plurals ignored, with the same exceptions ("shiitake mushrooms", "mushroom sauce"; not "coconut milk" for "no milk").
12. The Dietary Rules are a careful household guide, not allergen-certified. The existing disclaimer on the Dietary Rules screen stays as it is. A per-rule "Strict" option (fail closed again) is deferred until someone needs it.

## Consequences

- Recipe screens always show a status per line, and "You have X of Y" counts every line.
- A miss now leaves a Household Ingredient ("celery ribs" beside "celery" if the rules miss). Nobody will tidy these by hand, so matcher quality and catalogue growth are the real fix; the gap report is how we see them.
- A new food with hidden gluten and an innocent name passes a gluten-free rule. Accepted: false alarms were blocking good recipes, and the app says it's a guide.
- Household Ingredients don't convert units (ADR 0012), so "200 g andouille sausage" compares with the Kitchen as "have some" until it becomes a starter.
- Splitting "and" lines means a saved recipe can have more lines than were pasted; the review screen shows it.
- Every future table pointing at `ingredients` from recipe lines must keep NO ACTION (not SET NULL), and the merge must keep repointing them (`seed.MERGED_TABLES`, tested).
