# 0029: Recipe Images come from Unsplash, hotlinked and picked by eye

Date: 2026-11-20. Status: accepted. Replaces the sources, checking and storage parts of ADR 0027; its rule against scraping stands.

## Context

The 4f-a pipeline from ADR 0027 worked: Wikimedia Commons and Openverse found an openly licensed photo for 369 of 426 recipes, and a Haiku vision check (measured: 0 false passes on 41 labelled pairs) kept misleading ones out. But the product owner judged the photos too amateur for a premium app: home snapshots, uneven light, people's tables. Unsplash has professional food photography under a licence that allows commercial use.

Unsplash's API terms (read 2026-11-20) differ from Creative Commons in ways that shape the build:
- Apps must show the image URLs the API returns ("hotlinking"), not copies.
- Every displayed photo credits the photographer and Unsplash, with links back carrying `utm_source` and `utm_medium=referral`.
- Using a photo must be reported to its `download_location`.
- Any machine-learning or AI use of their content is covered by a separate data agreement.
- New apps get 50 requests an hour until approved for production.

## Decision

- **Source:** Unsplash search, landscape, `content_filter=high`. Up to four options per recipe.
- **Checking:** plain code only. An option is dropped if its description names a meat or fish the recipe doesn't have, or if it's smaller than 1200px. No model looks at Unsplash photos. The product owner picks one option, or none, per recipe on a local review page.
- **Showing:** the app loads photos from `images.unsplash.com`, sized and cropped to 4:3 by URL (960px hero, 360px cards, WebP at quality 55: about 150 KB and 30 KB, since these detailed photos stay over 120 KB even at quality 45). The URL is kept from the API, never from model output. Credit on the hero: a tiny "i" that shows the photographer's name, linked to their Unsplash profile (revised 2026-11-20: the product owner chose to drop "on Unsplash", knowing Unsplash's API guidelines ask for both names; revisit before launch).
- **Every Seed Recipe has a photo** (revised 2026-11-20, after the review): the product owner removed every Seed Recipe without a picked photo, 296 of 426, leaving 130. RecipeArt stays for Imported Recipes, Adaptations, and a photo that fails to load. Adaptations never show their parent's photo, since their dish has changed.
- **Parked:** the Haiku check and its eval, for if Unsplash agrees to an AI check; Magnific/Freepik as a backup source, once its licence is read (its site refused automated reads) and an API key is available.

## Consequences

- Better-looking photos, but the app depends on Unsplash's image server, and that server sees each viewer's request.
- No image files in git; ADR 0027's static folder and size limits go.
- Picking is human work: about 430 choices, one sitting or a few.
- The search runs about 9 hours in demo mode. Production approval needs the app to meet Unsplash's guidelines (credits shown), so apply after 4f-b.
- A smaller library (130): fewer dishes for plans and search; gaps get added later through the same checks, with a photo picked first.
- Second batch (2026-11-24): 105 drafted (ADR 0028), one photo searched each; 54 kept, the rest dropped (no photo, rejected, or a photo another recipe already uses). Library now 184. AI-made images stay parked.
