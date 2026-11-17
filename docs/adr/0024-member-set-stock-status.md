# 24. Members set stock status: In stock, Running low, Out

Date: 2026-11-17 · Status: Accepted · Amends ADR 0003

## Context

The Kitchen redesign (mockups in `docs/design/kitchen-redesign/`) shows every item with an In stock / Running low / Out badge that the Member taps to change, and Out items that stay on screen with an "Add to list" button. ADR 0003 only had Staples as have / run out and Tracked items as an amount with a calculated trust status, and "Finished" deleted the Tracked row.

## Decision

- Every Kitchen item has a **stock status the Member sets**: In stock, Running low or Out. It's stored (`low`, `ran_out_at`), not calculated.
- **Staple → Out** puts it on the Shopping List straight away (Undo toast). **Non-staple → Out** stays in the Kitchen as Out and only *offers* to add it ("Add to list?" toast).
- Out Non-staples are kept apart in the Kitchen view (`tracked_out`), so the planner, the agent and recipe matching never count them as "have". Running low still counts as have; the agent is told it's low.
- Staples have no amount: In stock / Running low / Out is all Sweep needs. Non-staple amounts stay, mostly filled in automatically (list ticks, Kitchen Photos, Cooked); they can be typed in any unit that honestly converts (kg → g; ml ↔ g only with a known density).
- Confirmed / Estimated / Unknown is still calculated (ADR 0003) and sent to the agent, but no longer shown on screen.
- Buying it (ticking it off the list) or a Kitchen Photo clears Out and Running low.

## Consequences

- Out Non-staples remember their place and amount, so "In stock" again is one tap.
- Two statuses on a Tracked item (stock + trust) — the screen shows only the Member's.
- Action toasts (Undo, Add to list) stay about 8 s and pause while touched or focused (WCAG 2.2.1); Undo is also safe to miss because the list item can be removed by hand.
- Cards show only the name and status (user, 2026-11-18): amounts stay in the background, editable through ⋯ → Change amount (Non-staples). No "how many" stepper: people won't keep counts up to date, and the status already drives decisions.
