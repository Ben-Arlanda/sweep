# 25. Planning screens: same Conversation, Dinner Ideas and Swaps by code

Date: 2026-11-18 · Status: Accepted

## Context

"Plan my week" and "Just tonight" are moving out of the chat and onto their own screens: Generating, then the ideas or the plan review, then a saved screen. The chat stays only as "Ask Sweep to tweak". The new screens also ask for two things the agent can't do today:

- show three dinner ideas for tonight and let the Member pick one;
- swap one day of a pending plan for an alternative before approving it.

## Decision

- **The screens are a new front end on the same process.** "Generate my plan" still starts a Conversation turn with the Plan Mode and Plan Days (ADR 0015). The streamed tool events become the Generating checklist, the Proposal is shown as the Review screen, "Add to my week" is approve, and "Refine with Sweep" is a message that supersedes the Proposal (ADR 0014). We considered a separate plan endpoint without a Conversation. It was rejected because it would duplicate approvals, validate, tracing and evals.
- **Dinner Ideas come from code, not the agent.** A plain API route returns tonight's best Kitchen Matches that pass the Dietary Rules, using the same ranking as `recipes_from_kitchen` (ADR 0013). Picking one saves the Planned Meal directly. The Member is choosing, the same as editing the Meal Plan by hand, so there's no Proposal. The agent only runs when the Member asks for a tweak, and that ends in a normal one-dinner Proposal. We rejected letting the agent pick three options: each tap would be a paid call taking 5–10 s, and the Draft and Proposal would need an "options" shape.
- **A swap is a fourth resume, handled by code.** Besides approve, reject and message, the paused `approve` node accepts `swap {day, recipe}`. A code node changes that day in the Draft, recalculates the List Additions whose reason is that day's meal (keeping additions the Member asked for), runs the usual validate checks, supersedes the old Proposal and shows a new one. It works like `reshow`, with no model call. The alternatives come from the same code as Dinner Ideas (taste search in New recipes mode), excluding recipes planned on other days.

- **Talking to Sweep stays on the screen.** "Refine with Sweep" and the Dinner Ideas tweaks send a message from a bottom sheet. The chef shows while it works, the screen refreshes with the new Proposal, and the agent's reply appears as a short note. The full Conversation stays reachable from the screen's menu. Replies are therefore one or two sentences, which an eval check enforces.

## Consequences

- Swaps and Dinner Ideas are instant and free, and the Member picks the replacement themselves.
- A Proposal still never changes. Each swap leaves a superseded row, which also records what Members swap away from.
- The next agent turn must see the current Draft, including swaps, so the model doesn't undo them.
- The Generating screen for Just tonight has almost nothing to wait for, so it shows a brief branded moment.
