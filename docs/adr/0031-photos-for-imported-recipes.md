# 0031: A Member's own photo on their Imported Recipes, stored privately

Date: 2026-11-20. Status: accepted. Builds on ADR 0029 (Seed Recipe photos) and the recipe import doors (ADR 0020). Brings forward the "Member photos for Imported Recipes" parked in docs/plan.md, without waiting for slice 11.

## Context

Every Seed Recipe now has a stock photo. A Member's own recipes showed a guessed emoji; the product owner wants a plain food icon there, and the choice to add their own photo: when they add the recipe and any time later (usually after cooking it). Sweep has never kept a photo a Member took: Kitchen and recipe-import photos are read and thrown away.

## Decision

1. **Where:** a photo slot at the top of the review screen (every import door ends there, and Edit uses it too), and Add / Change / Remove photo on the recipe page of the Member's own recipe. Not in the Add menu: that picks where the recipe comes from.
2. **What:** one photo per Imported Recipe. Seed Recipes keep their Unsplash photo; Adaptations show no photo (their dish changed); with no photo, a plain food icon (`Utensils`, knife and fork) on the recipe's pastel.
3. **Upload:** the phone shrinks the photo to JPEG first (as the import doors do, which also turns HEIC into JPEG). The server takes JPEG, PNG or WebP, up to 5 MB, the type read from the file's first bytes.
4. **Stored clean:** the server decodes the image (refusing very large pixel counts), turns it upright, crops it to 4:3 and saves two new WebP files, 960 and 360 px wide. Re-encoding keeps only the pixels, so GPS location and camera details are gone. The original is never stored.
5. **Private:** files sit under the Household's own folder. The API returns short-lived signed links (an HMAC of the recipe, photo and an expiry, valid about an hour, rounded so a link stays the same for caching). The photo route checks the signature, not a sign-in header, so it works in `<img>` and expo-image on every platform, the way S3 presigned links will.
6. **Storage behind one interface** (`PhotoStore`: put, get, delete, delete a Household's folder). Development uses a folder on disk (`PHOTO_DIR`, git-ignored); slice 11 adds S3 with the same interface. The signing key is `PHOTO_SIGNING_KEY`; without one, each server start makes a random key (old links stop working, which is fine in development).
7. **Deleted with what owns it:** replacing or removing a photo deletes its files; deleting the recipe deletes them; the last Member leaving deletes the Household's whole folder.

## Consequences

- The feature works now on the Mac-hosted API; production needs S3 (slice 11), since a hosted server's own disk is wiped on restart and not shared between copies.
- A file delete can fail after the database change commits, leaving an unreachable file; slice 11 can add a clean-up of files no recipe points at.
- Photos are not checked for content: they are only ever shown to the Household that uploaded them.
