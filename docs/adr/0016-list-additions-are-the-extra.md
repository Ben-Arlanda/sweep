# 16. A proposed list addition is the extra on top of the Shopping List

Date: 2026-11-15 · Status: Accepted

## Context

6b's end-to-end run showed a re-proposal repeating ten items the last approval had already added; approving skipped them all. Worse, it skipped "8 sausages" because 4 were already on the list, leaving the list 4 short. The product owner chose to fix both ends: the agent proposes only what's missing, and approving raises an amount already on the list.

## Decision

- **One meaning:** a List Addition's amount is the extra to buy, on top of what's already on the unticked Shopping List. Both ends follow it, so nothing is counted twice.
- **The agent proposes only the extra.** `check_kitchen_coverage` subtracts the matching unticked list item (same Ingredient), converted with the same unit rules as the Kitchen (ADR 0003): `missing` holds only the extra, `on_list` what the list already covers. The prompt says to add exactly what's missing. Plain sums, never the model's arithmetic.
- **Approving tops up.** An addition matching an unticked item (same Ingredient, else same name) raises that line, kept in its own unit (`1 kg` + 500 g → `1.5 kg`); it stays one line, the Member's own if they added it. Ticked items are never touched: ticked means bought.
- **Refuse to guess.** If either amount is missing, or the units don't convert ("1 jar" and grams), the addition is skipped with what to check ("…with no amount: make sure it covers 300 g more").
- **Said on the card.** Each addition shows what's already on the list ("4 more sausages (4 on the list)"); the outcome lists every top-up ("rice: 500 g → 800 g").

## Consequences

- A Proposal made before this decision carries totals, not extras; approving one could over-count. Only Proposals pending at release time are affected.
- The list doesn't know which meal an item is for: if a planned meal is replaced, its items stay on the list for the Member to remove.
