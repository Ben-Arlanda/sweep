# 0020: Recipe imports: one Haiku call, checked by code

Date: 2026-11-17. Status: accepted.

## Context

Slice 4d lets a Household bring in its own favourite recipes, from wherever they live: pasted text, photos of a cookbook, a link, a PDF print-out, or typed. That text is messy, comes from anyone, and can try to give orders to the model (prompt injection). Imported Recipes then feed the agent and the Shopping List, so a wrong or invented line has real consequences: something bought for nothing, or a Dietary Rule broken.

## Decision

**One model call per import, with no tools. Code checks the answer and does everything after it.**

- **Paste, photo, file: one Haiku call** (structured output: title, servings, minutes, Course guess, cuisine, lines as written, method). Low effort: it's copying and sorting, not reasoning.
- **Link: no model at all.** Our own small reader takes only schema.org JSON-LD from the page (facts plus `source_url`, never the method). The fetcher allows `https` and public addresses only, checked at connect time and on every redirect, follows robots.txt for `SweepBot/1.0`, and has size and time limits. No JSON-LD means "paste the text instead". We chose this over recipe-scrapers, which would bring about 10 HTML/RDF parsing packages to run on hostile pages.
- **The text-appears check:** every line the model returns for text (pasted or from a PDF) must appear in that text, comparing letters, numbers and punctuation exactly and ignoring case and all spacing. A line that doesn't appear gets a "Check" mark. It never blocks, but a made-up line like "50 saffron threads" can't get through unmarked. Photo and scanned-PDF lines are all marked Check.
- **Matching is rules only** (`ingredient_lines`), with **no LLM line fallback**. An unmatched line is "Not linked" for a Member to link by hand. Lines are never linked to a near-miss.
- **PDFs:** pypdf runs in a spawned child process that is killed after 10 s, because a hostile PDF can make a parser hang and a thread can't be stopped. A PDF with text takes the Paste path; a scan goes to the same Haiku call as a `document` block.
- **Dietary Rules fail closed:** with any Rule active, a line linked to a Household Ingredient (whose contents Sweep doesn't know) counts as "couldn't check", so the recipe isn't planned or shown in search.
- **Limits:** 20 import attempts per Member per hour, counted in Postgres. Calls count toward the daily token budget shared with the agent.
- **Nothing is stored until Save**, and photos and files are never stored.

## Evidence

`python -m evals.recipe_import`: 13 cases, graded in code with no judge model. 9 are made up (including an injection paste and a PDF with hidden white text, both with Canary saffron). 4 are the product owner's own (photos, a scan, two RecipeTin print-outs) and are git-ignored.

- First run, Haiku ×3, 2026-11-17: **33/39 for 2.2¢** (about 0.06¢ an import). Both Canaries stayed out every time. All 6 failures were the two print-outs. A print-to-PDF splits a line's note onto the next line (`2 garlic cloves ⏎ , grated (Note 3)`) and Haiku dropped those halves, and the matcher didn't know `180g/6 oz` amounts.
- Fixed by **rules, not prompting:** lines starting with `,` or `(` are joined back on, the metric half of `180g/6 oz` is kept, `A / B` is read as `A or B`, and there are new starters. Not linked on those PDFs dropped from 14 to 1, and 0 of the 4,373 Seed Recipe lines changed.
- Photos read well on Haiku (11/11 lines on a 2-page cookbook recipe), so **no Sonnet** for photos.

## Consequences

- **The model can be fooled without harm.** The worst a bad reading can do is put lines on a review screen, marked, for a person to fix before Save. It can't save, link Ingredients or touch a Shopping List.
- **Messy layouts need rules for each source.** Each new kind of source (a site's print style, a cookbook's wording) can need a parser rule or starter, found by running real examples through the eval. Every parser change is checked against all Seed Recipe lines.
- **Some fields stay null:** when PDF text puts labels far from their numbers, Haiku may leave servings or time empty. That's an honest answer, and the review screen asks for them. One known wrong reading: a RecipeTin time taken from the optional marinade.
- **"1 beef stock cube" stays Not linked** on purpose. As an alias of "stock cubes" (only "check the label" for meat) it would pass a vegetarian Rule.
- **The eval must use the app's own steps**, never a copy. It now calls `paste_text_from_pdf`. A copy had once kept a fix from being measured.
