# 1. Use a simulated supermarket catalogue, not live supermarket data

Date: 2026-11-08 · Status: Accepted

## Context

The brief targets Coles, Woolworths and Aldi. Research (Nov 2026) found no official public developer API from Coles or Woolworths. Only unofficial third-party scrapers exist, which likely conflict with the retailers' terms of service and break when the sites change. The product owner confirmed live pricing is not needed. The core value is the connected Cabinet, Shopping List and Recipe Knowledge Base.

## Decision

- Prices come from a **simulated catalogue** we own: Ingredient → store → pack size → Estimated Price, with `source = simulated` on every row.
- The UI always shows prices as **Estimated** and never as real shelf prices.
- No scraping of supermarket sites, now or as a "temporary" measure.
- Pricing sits behind a `PriceProvider` interface so a licensed or official source can be added later without touching the agent.

## Consequences

- We can't claim "saves you money vs. Coles". The product promise becomes "plan from your Cabinet, shop together, ballpark cost".
- Budget validation still works, against estimates.
- Product-level basket optimisation (cheapest pack combination) becomes a later experiment, since optimising fake prices has little product value.
- Revisit if an official data program or licensed dataset appears (the ACCC has pushed for supermarket price transparency).
