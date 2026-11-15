# 10. No prices or budgets

Date: 2026-11-15 · Status: Accepted · Supersedes [ADR 0001](0001-simulated-supermarket-catalogue.md)

## Context

The brief asks for budget validation and a "cheapest sensible basket". There are no official supermarket price APIs, so ADR 0001 planned a simulated catalogue. Checking against `AI_LEARNING_ROADMAP.md`, no learning objective depends on prices: the deterministic-tool, constraint-replan and deterministic-vs-LLM lessons are already covered by Cabinet coverage, Dietary Rules in the validate loop, and the slice 8 baseline planner. Made-up prices would also make any "cost" number misleading for real users.

## Decision

- No catalogue, no Estimated Price or Estimated Cost, no `estimate_cost` tool, no budget validation.
- The weekly budget Preference (added in 5b) is removed from the schema, the API and the Food rules screen.
- Slice 7 and experiment E3 (basket optimisation) are dropped.

## Consequences

- The product promise loses "with a ballpark cost". This is a deliberate change from `PRODUCT_BRIEF.md`, made by the product owner.
- Shops (ADR 0009) are labels only, so Households can add any Shop without needing price data.
- Revisit if a licensed or official price source appears; it would need a fresh ADR, not a revival of the simulated catalogue.
