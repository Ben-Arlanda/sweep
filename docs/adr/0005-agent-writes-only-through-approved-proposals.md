# 5. The agent writes only through approved Proposals, scoped by the server

Date: 2026-11-08 · Status: Accepted

## Context

The agent is a genuine LangGraph agent that picks its own tools. That freedom is the point, but it can't extend to changing Household data unchecked or reaching another Household's data. Prompt injection via Imported Recipe pages is a realistic threat.

## Decision

- **The agent has no tool that writes Household data.** Its tools fall into three groups:
  - *read* (recipes, Cabinet, preferences, Shopping List)
  - *compute* (deterministic: Cabinet coverage, Estimated Cost)
  - *draft* (edit the Draft Plan held in agent state)
- A `propose_plan` tool ends the turn. The graph moves to a validation node, then an **`interrupt()`** that shows the Proposal. Only after an Approval does a deterministic `commit` node call the same services the REST API uses, under the approving Member's permissions. The Proposal id is the idempotency key.
- **`household_id` and `member_id` are never tool arguments.** They are injected from the authenticated request into the graph's runtime config. The LLM cannot pick a different Household.
- Commit re-validates against *current* data (a Member may have edited the list while the Proposal waited). Proposals expire after 24h.
- Every Proposal, Approval, rejection and commit is written to an append-only audit log.

## Consequences

- One extra tap for the Member compared with letting the agent write directly. That's intended, and it's the brief's human-in-the-loop objective doing a real job.
- Draft editing ("swap Tuesday") is cheap and needs no approval until the Member proposes again.
- An injected instruction can at worst produce a bad *Proposal*, which a human sees before anything changes.
