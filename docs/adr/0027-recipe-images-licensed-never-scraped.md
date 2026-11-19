# 0027: Recipe Images are openly licensed or Sweep's own, never scraped

Date: 2026-11-19. Status: accepted. Builds on ADR 0002 (recipe sources). Reopens the "no meal photos" call in slice 6c, now that there is an image source and a licensing rule.

## Context

Recipes show emoji art (`RecipeArt`), and the product owner wants real images. The quickest source is scraping food photos from the web, but a photo with no licence is "all rights reserved" by default, several recipe sites forbid bots, and a scraped photo would show someone else's dish beside our own recipe. We already rejected a scraped recipe set for the same reason (ADR 0002). Free photo searches return *a* dish of that name, not ours, so a picture can mislead (prawns on a vegetarian recipe).

## Decision

- **Sources:** Openverse and Wikimedia Commons, accepting only CC0, Public Domain, CC BY and CC BY-SA. Never NC (Sweep is a product) or ND (we crop and resize). Each image keeps its author, licence and source, and the recipe screen credits it under the hero.
- **Checked before shown:** a Haiku vision check (measured first on labelled pairs) rejects wrong dishes, clashes with the recipe or Dietary Rules, unfinished dishes, watermarks, text and faces. The product owner signs off the first full run on a contact sheet.
- **Small files:** WebP at 960px (≤ 70 KB) and 360px (≤ 15 KB), enforced by a test.
- **Storage:** files in the API's `static/recipes/` folder, committed to git; they move to S3 + CloudFront in slice 11. Image URLs come only from our database, never from model output.
- **No image is fine:** recipes without an approved image keep `RecipeArt`. AI-generated images are parked until we see the coverage.
- **Member photos for Imported Recipes are deferred** until after slice 11: they're private to a Household, so they need a private bucket, signed URLs, EXIF stripping and deletion, and Sweep stores no user photos today (ADR 0020, 0023).

## Consequences

- Coverage will be incomplete: common dishes will have photos, unusual ones may not.
- "Close" matches mean a photo can be a similar dish rather than this exact one.
- About 30 MB of images in git; Git LFS if it grows.
- A disputed licence affects one image, which can be found from its credit record and swapped.
