# 0033: Ingredient Groups keep a recipe's ingredient headings

Date: 2026-11-22. Status: accepted. Amends ADR 0020 (the import left headings out).

## Context

A RecipeTin Eats salmon tray bake (PDF) lists its ingredients under "Marinade slather:", "Vegetables (optional):" and "Cooking & serving:". The import saved one flat list of 17 lines because the reading prompt said to leave headings out. Step 1 says "Mix the marinade ingredients", and olive oil appears twice (2 tbsp in the marinade, 2 tsp on the vegetables): without the headings you can't follow it.

## Decision

1. A recipe line may belong to an **Ingredient Group**, named by its heading ("Marinade slather"). Stored as `recipe_ingredients.group_name` (nullable, 80 characters); a group is the run of consecutive lines with the same name. No separate table: a group has nothing but a name and an order, and lines already have both.
2. The Paste, Photo and File doors' one model call also returns `ingredient_headings`: `{before_line, heading}` pairs pointing at the lines it already copied, never the lines again. Code checks them: a position in range, a heading of one line (trailing ":" removed), and for pasted text, found word for word in it (as lines are); otherwise it's dropped. No extra call.
3. The review screen and the recipe screen's Ingredients tab show each group's name above its lines. A line typed on the review screen joins the last group. "salt and pepper" split into two lines keeps its group; Adaptations copy it.
4. A PDF with text also sends its layout text (pypdf's `layout` mode: the order on the page, though light-grey notes can be missing). The model copies from the plain text and uses the layout only to place headings; code checks a heading against the start of its line in the layout. About $0.0003 more per PDF import; page images would cost about 10 times that and couldn't be checked by code.
5. Link imports stay flat: a site's recipe data (schema.org) has no groups. Seed Recipes have none for now.
6. The Shopping List, the Kitchen match and the Dietary Rules ignore groups.

## Consequences

- Recipes read the way they were written; "the marinade ingredients" means something.
- The reading's output grows by a few tokens per heading (fractions of a cent).
- The recipe import eval gains a grouped case, so a model change that drops headings shows up.
