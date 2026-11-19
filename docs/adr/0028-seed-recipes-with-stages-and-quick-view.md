# 0028: Seed Recipes have Recipe Stages, with Quick View steps generated and checked

Date: 2026-11-19. Status: accepted. Revises ADR 0002 (recipe sources) and slice 4c's library; builds on the Cookable Method checks from 4e.

## Context

The 500 Seed Recipes from slice 4c had short methods. The 4e audit made them pass the Cookable Method checks, but the product owner found they still read thin next to a good cookbook recipe, and asked for a fuller recipe as well as the quick steps cooks already liked. The product owner drafted 500 richer recipes with their own AI, in a fixed JSON shape (stages with minutes, tips, variations, storage). A third of them came back thin or padded with filler.

## Decision

- **Replace the library.** The product owner's 500 recipes become the Seed Recipes. The old ones are deleted (test users only; cascades are fine).
- **Two views of one method.** A Seed Recipe stores Recipe Stages (the Detailed View) and 3–6 short `method` steps (the Quick View). The app opens in Detailed; a switch shows Quick and is remembered on the device. Cook Mode steps through whichever view is showing, with the screen kept awake.
- **Quick steps are generated and gated.** Claude writes the quick steps from the stages. They go in `method`, so the agent, Adaptations and Kitchen Match keep working unchanged. Both views must pass the same deterministic checks. The LLM reviewer also checks that they describe the same cooking. Generated content is never trusted without that gate, and that applies to the 193 thin recipes Claude rewrote too.
- **Seed files are JSON.** TOML is awkward for nested stages.
- **Titles** lose a country prefix that only repeats the cuisine ("Japanese Oyakodon" → "Oyakodon"), keep one that names the dish ("Greek salad"), and use sentence case. The product owner approves the list, and the duplicates.

## Consequences

- Two texts per recipe can drift apart. The checks and the reviewer catch that at build time, and a person signs off.
- The Retrieval Set and other eval labels point at old slugs, so they're relabelled and re-measured. The numbers aren't directly comparable with slice 9.
- Imported Recipes keep one view (no stages).
- Drafting by an LLM means mistakes a cook would spot can slip through the checks; the product owner's spot check stays.
