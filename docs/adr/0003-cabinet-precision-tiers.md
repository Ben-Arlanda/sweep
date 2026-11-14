# 3. The Cabinet uses precision tiers, not exact stock-keeping

Date: 2026-11-08 · Status: Accepted

## Context

The brief asked for exact quantities, deductions and duplicate prevention for every ingredient. Real kitchens drift: unlogged meals, purchases made without the list, staples nobody measures. A Cabinet that is confidently wrong loses Members' trust, they stop updating it, and the connected product stops working.

## Decision

- Ingredients in the Cabinet are either **Staples** (have / run out, no quantity) or **Tracked Ingredients** (quantity + unit).
- Tracked quantities carry a status: **Confirmed**, **Estimated** or **Unknown**.
- Status is **calculated when it's read**, from `last_confirmed_at` and the source of the last change. Estimated → Unknown after a configurable period (start: 14 days). No background job is needed.
- The agent treats the Cabinet as a hint. Every Proposal lists the Cabinet assumptions it relies on so the Member can correct them in one tap.
- All quantity maths (unit conversion, deduction, merging) is deterministic backend code.
- Only **Cooked** meals deduct. Adding a meal to a Meal Plan never does.

## Consequences

- Less "impressive" than gram-perfect tracking, but it survives real use.
- Needs a per-Household setting for which Ingredients are Staples (with sensible defaults).
- The brief listed recipe-based consumption as a later enhancement. We pull "mark as Cooked" into the MVP because it's cheap with this model and keeps Tracked quantities meaningful.

## Implementation notes (slice 3, 2026-11-14)

- **Thresholds:** Confirmed for 7 days after a purchase or manual edit, Estimated after that (and straight away after a Cooked deduction), Unknown after 14 days without confirmation. Constants in `app/services/cabinet.py`.
- Quantities are stored only in the Ingredient's base unit (g, ml or count). `quantity = null` means "have some, amount not recorded". Conversions that would need a guess (a count to grams, or millilitres to grams without a known density) give null rather than a made-up number.
- **Ticking a linked item** adds the converted amount as Confirmed. If the existing entry is Unknown, the purchase replaces it, because the old amount isn't trusted. Ticking a Staple marks it "have". **Unticking** takes back what that tick added (best effort). Relinking a ticked item moves its stock to the new Ingredient.
- Ingredient matching is strict: exact name, alias, or a simple plural. Unmatched items stay off the Cabinet. Smarter matching is slice 4.
- Ingredients are reference data loaded by migrations (`app/seed.py`). New Households copy the default Staples, and Members can change them.
