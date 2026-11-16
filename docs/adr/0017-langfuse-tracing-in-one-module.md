# 0017: Langfuse tracing, written by hand in one module

Date: 2026-11-16. Status: accepted.

## Context

Slice 8 needs traces: what the agent saw and did on each turn, so a failing eval run (or a strange chat) can be replayed step by step, with tokens and cost per model call. Plan §11 chose Langfuse; the product owner chose Langfuse Cloud (EU) in the slice 8 grilling. Langfuse's guide ("What does a good trace look like?") asks for one trace per chat turn, one session per conversation, one generation per model call (not one around the agent loop), tools as siblings of the generation that asked for them, and stable verb-first names.

Langfuse recommends a framework integration first. Ours don't fit well: the agent calls Claude through the `anthropic` SDK's beta streaming API inside LangGraph nodes (ADR 0008), not through LangChain, and we needed our own cost figures (cache reads, cache writes and thinking tokens priced as Anthropic bills them).

## Decision

- **One module, `app/tracing.py`, is the only code that imports Langfuse** (as `app/llm.py` is for Anthropic). The rest of the app calls `tracing.turn(...)` and `tracing.observe(...)`; with tracing off they are no-ops.
- **Observations by hand, in the graph:** `plan-meals-turn` / `decide-on-plan` (agent, the trace root, in the Conversation's session, user = Member UUID) → `load-household-context` (retriever) → `choose-next-step` (generation, per model call) → each tool by name (`retriever` for lookups, `tool` otherwise) → `validate-plan` / `reshow-plan` (guardrail) → `save-approved-plan`. The generation is in the graph's `agent` node, around `AgentModel.respond`, so any model (scripted in tests, Bedrock later) is traced the same way.
- **Our cost, not Langfuse's guess:** each generation sends usage by token kind and `cost_details` from `app/llm_costs.py`, so Langfuse and the evals report the same numbers.
- **Only our spans are exported** (`should_export_span = is_langfuse_span`). The Anthropic SDK emits its own generation span per call, which Langfuse exports by default: the first live trace showed every call's cost counted twice, and the SDK's copy priced without the thinking tokens.
- **Off by default in tests:** keys come from `.env`, which tests also read, so `conftest.py` sets `LANGFUSE_TRACING=false`. Tests use the real SDK with an in-memory exporter. Tracing starts in the app's lifespan, not in `create_app`.
- **Environments:** `development` for the dev server, `eval` for eval runs (tagged `eval`, `scenario:<name>`, with run and repeat in metadata).

## Consequences

- About 150 lines we own instead of an integration. In return: no duplicate spans, correct cost, and traces that survive a provider change.
- **Data leaves the machine.** Traces hold the Member's messages, the per-turn Household context (Dietary Rules, which can include allergies; the Kitchen; Preferences), tool arguments and results, and replies. No names or emails. Acceptable while only test Households exist; **before real users** this needs a privacy notice and either masking (`mask_otel_spans`) or self-hosting (slice 11).
- Thinking blocks are recorded but empty: Claude 5.5 models return thinking as `display: "omitted"` by default. Showing summaries is a separate, small API change (open item).
