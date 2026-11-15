# 9. One Shopping List per Household, with Shops as item labels

Date: 2026-11-15 · Status: Accepted

## Context

Slice 2 let a Household make several Shopping Lists. In practice a Household shops together, and the reason people split lists is *where* they'll buy things (Coles vs Aldi), not *who* is buying. Several lists also forced a "which list?" choice on every agent Proposal.

## Decision

- **Exactly one Shopping List per Household** (`UNIQUE (household_id)`), created with the Household. Existing extra lists were merged into the oldest one.
- Items carry an optional **Shop** (`shop_id`, `ON DELETE SET NULL`). No Shop means "any shop".
- **Shops belong to the Household.** Every Household starts with Coles, Woolies and Aldi; any Member can add, rename or delete one. Deleting a Shop returns its items to "any shop", so nothing is lost.
- Shop changes bump the list's version and send the usual change notice, because they change how the list looks. Devices refetch one `GET /list` that includes items and Shops.
- Item routes keep the list id in the path (`/lists/{id}/items/...`). The id still scopes the row lock, the version and the offline retry queue, so slice 2's sync design (ADR 0004) is unchanged.
- UI: tag an item from a bottom sheet; choose a Shop with chips when adding (last choice remembered per device); filter by Shop, where a Shop filter also shows untagged items.

## Consequences

- No list picker anywhere, including on Proposals. Agent additions land on the one list, untagged.
- Filtering is client-side over one list; at household scale (≤500 items) that's instant.
- A Household that really wants a separate list (a party) uses a Shop label for it. If that proves awkward, revisit with "collections" rather than bringing back lists.
