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
