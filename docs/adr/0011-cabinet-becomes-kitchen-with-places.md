# 11. The Cabinet becomes the Kitchen, organised by Place

Date: 2026-11-15 · Status: Accepted

## Context

"Cabinet" was chosen early (CONTEXT.md) to avoid "pantry" and "inventory". In use it read oddly: a cabinet doesn't hold milk or frozen peas. People think about food by where it lives: the fridge, the freezer, the cupboard. The old screen grouped by how we track things (Tracked vs Staples), which is our model, not theirs.

## Decision

- **Rename Cabinet → Kitchen everywhere**: UI, CONTEXT.md, code, routes (`/kitchen`), tables (`kitchen_items`, `households.kitchen_version`, `shopping_list_items.kitchen_*`), the change-notice entity, and the agent's tools (`get_kitchen`, `check_kitchen_coverage`). The migration renames tables, columns and constraints in place, so no rows are lost. ADRs 0001–0010 keep the word "Cabinet" as written; read it as Kitchen.
- **Place** is Fridge, Freezer or Cupboard. Each Ingredient's default Place comes from its category, in code (`app/data/places.py`), like Dietary Rule data:
  meat, seafood, dairy, chilled → Fridge · frozen → Freezer · pantry, spices, bakery, drinks → Cupboard · produce → Fridge, except a short list kept out of the fridge (onions, garlic, potatoes, bananas…).
- A Household can **move** a Tracked item or a Staple to another Place (`PUT /kitchen/places/{ingredient_id}`); `null` puts it back to the default. The override is stored on the item, so it disappears with it.
- The Kitchen screen groups by Place with filter chips **All · Fridge · Freezer · Cupboard**. Tracked vs Staple still decides what a row shows (an amount and a status, or have / run out), but it's no longer how the screen is organised.
- The agent's tools are unchanged in behaviour. Place is a way of looking at the Kitchen, not a planning input.

## Consequences

- Saved agent conversations from before the rename mention the old tool names. They're dev test data only; "New plan" starts fresh if one misbehaves.
- The default-Place table will be wrong for some households (soy sauce in the fridge, bread in the freezer). That's what the per-item override is for.
