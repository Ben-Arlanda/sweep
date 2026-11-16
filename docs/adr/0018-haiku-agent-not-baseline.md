# 0018: The agent runs on Haiku; the simpler baseline is not adopted

Date: 2026-11-16. Status: accepted.

## Context

Slice 8 built agent evals (Scenarios run on the real graph, graded by deterministic checks, priced from tokens) and a Baseline Planner (code filters by Dietary Rules and ranks by Kitchen Match, one model call picks; no tools, no replans). Both ran on Claude Sonnet 5.5 and Haiku 5.5.

Results, 2026-11-16:

| | Agent · Sonnet | Agent · Haiku | Baseline · Sonnet | Baseline · Haiku |
|---|---|---|---|---|
| All 15 Scenarios × 3 | 45/45 | 44/45 (the reshow gap, fixed, then 6/6) | n/a | n/a |
| 12 single-message Scenarios × 3 | 36/36 | 36/36 | 36/36 | 36/36 |
| Replans needed | 0 | 0 | none (no validate) | none |
| Things to buy per meal | 4.6 | 4.4 | 2.7 | 2.6 |
| Seconds per plan | 12.0 | 13.4 | 3.6 | 4.0 |
| Cost per plan | 3.49¢ | 0.26¢ | 1.42¢ | 0.09¢ |

The checks are a safety floor (real recipes, Rules kept, the right days, the right count), not a quality score. Read by hand, the baseline's plans were often poor dinners: green beans, a mango dessert and Spanish prawns for a Household that asked for Thai; jaffles and crepes in a Kitchen week. Its low "things to buy" comes partly from those choices. A blind review page was built (agent and baseline on both models, labels hidden); the product owner chose not to complete it.

## Decision

- **The agent's default model is Claude Haiku 5.5** (`agent_model`, was Sonnet 5.5). It matched Sonnet on every check at about 1/13 the cost and similar speed. `AGENT_MODEL=claude-sonnet-5-5` switches back.
- **The agent stays; the Baseline Planner is not adopted.** It is faster and cheaper but its plans were visibly worse, and it cannot do follow-ups ("swap Tuesday", reject then revise), which need a conversation.
- **No provider switch now.** The evals show the model is not the limit on these Scenarios: the cheapest one passes everything. A different provider (e.g. a GPT model) would be compared on the same evals first (experiment E5).

## Consequences

- **Plan quality was not measured**, only safety. Real use is the quality check; if plans feel worse, re-run `python -m evals.agent --model sonnet` and compare. The blind review page (https://claude.ai/artifact/N3QoQsU5M4TE4N3fQDiDtK) stays available.
- **No server-side refusal fallback on Haiku.** If its safety filter declines a request, the Member sees "Sorry, I can't help with that one" instead of Sonnet taking over. Not seen in any eval run.
- **The weak spots found are data, not model:** recipes aren't labelled as mains, sides or desserts, and "New recipes" can't surface a cuisine the Kitchen ranking pushes down. These are follow-ups in the plan; fixing them should improve plans more than a bigger model would.
- Re-run the evals before changing the model, the effort, the prompt or the tools.
