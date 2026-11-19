# 0022: Meaning search (R1) stays; keyword, hybrid and rerank don't ship

Date: 2026-11-17. Status: accepted.

## Context

Slice 9 compared four ways to search the Recipe Knowledge Base on one Retrieval Set (51 queries, 28 dev / 23 test, 7 kinds of query; see CONTEXT.md):

- **R1 meaning** (the product): Voyage query vector, pgvector cosine distance, after the SQL filters.
- **R2 keyword:** Postgres full-text search over a weighted document (title, Ingredient names *and their aliases*, cuisine and summary), any word, `ts_rank_cd`.
- **R3 hybrid:** reciprocal rank fusion of R1's and R2's top 30.
- **R4 rerank:** Voyage `rerank-2.5` re-orders R3's top 30.

The bar was set before any results: replace R1 inside `recipes.search()` only if a method gains **≥ 5 points on recall@10 or MRR@10 on the test queries**, is no worse on the other, and adds **< 50 ms p95**.

Labels: written against an intent line written before any method ran; pooled from every method's top 20 plus every recipe using a named Ingredient; 20 queries labelled by SQL rules over the recipe lines, 31 by hand from the full catalogue. 0 unjudged recipes in any method's top 10 in the final run.

Results on the **test** queries, 2026-11-17 (`python -m evals.retrieval --rerank`):

| | recall@10 | P@10 | MRR@10 | recall@60 | extra time |
|---|---|---|---|---|---|
| R1 meaning | 0.516 | 0.457 | 0.825 | 0.855 | (today) |
| R2 keyword | 0.380 | 0.400 | 0.688 | 0.696 | faster, no Voyage call |
| R3 hybrid (k 60) | 0.509 | 0.474 | 0.826 | 0.823 | +2 ms |
| R3 tuned on dev (k 20, keyword ½) | 0.519 | 0.483 | 0.829 | | +2 ms |
| R4 rerank | **0.593** | **0.583** | **0.965** | 0.823 | **+430–670 ms** (live call) |

By kind, keyword search wins only where words differ: "aubergine", "shrimp", "garbanzo beans" (aliases in its document; the embedding text has none). It loses badly on moods ("cosy winter dinner": MRR 0.15 vs 0.69) and negation.

## Decision

- **R1 stays.** R3 doesn't reach the bar even on the dev queries it was tuned on (+2.4 recall, −1.1 MRR), and on test it's level with R1.
- **R4 is far better at ordering** (+7.7 recall@10, +14 MRR on test; first good answer nearly always at #1) **but misses the time bar by about 10×**, costs a call per search, and Voyage's free tier allows 3 requests a minute: the Recipes tab would hit that at once. It doesn't ship.
- **R2 and fusion stay in the code** (`recipes.keyword_search`, `recipes.fuse`, the `search_document` column, refreshed on seed load, import and edit) so the eval is reproducible and the follow-ups below are cheap. Nothing in the product calls them yet.

## Consequences

- **Reranking is the method to revisit** if search quality becomes a complaint: with a paid Voyage plan, only where a person waits anyway (e.g. the agent's `search_recipes`, where a turn already takes ~12 s), not on every Recipes tab keystroke. Re-run the eval first.
- **Follow-up, data not method:** add Ingredient aliases to `embedding_text` and re-embed (about 30k tokens), then re-run. It should close R1's gap on "words" queries, the one place keyword search beat it.
- **Follow-up, reliability (DONE 2026-11-18):** when Voyage is unavailable (often the free tier's ~3 calls a minute), `search_or_keywords` falls back to R2 instead of an error, for the recipe search screen, `search_recipes` and `recipes_from_kitchen` (R2 alone still finds about half of what R1 does).
- **Fused lists are shallower:** R3/R4 recall@60 is 0.82 vs R1's 0.86, because they only merge two top-30s. `recipes_from_kitchen` takes 60 candidates, so a fused method would need deeper lists there.
- **The Retrieval Set is optimistic:** Claude wrote both the recipes and the queries. Real search logs (none yet) would make a harder, fairer set.
- Re-run `python -m evals.retrieval` after changing the embedding text, the embedding model, the filters or the seed library.
