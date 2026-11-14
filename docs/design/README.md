# Design direction

Status: direction agreed 2026-11-14, design system not built yet. Built in a design-foundations slice (proposed as slice 3b, needs adding to plan §14).

## Goal

A premium, public-ready app that is **colourful and bright** and grabs attention, not a muted utility look. It should still feel calm and quick to use in a supermarket: one hand, quick glances, bad light.

## Inspiration sources

Browse these by hand, save what you like, and note why:

| Source | Use it for |
|---|---|
| [Mobbin](https://mobbin.com) | Real shipped mobile flows: onboarding, lists, tab bars, empty states. Paid; needs a login. |
| [Dribbble](https://dribbble.com) | Visual direction: colour, illustration, cards, motion. Often concept work that was never shipped. |
| [Behance](https://www.behance.net) | Full case studies: complete brand and app systems, and the reasoning behind them. |

**Rules:** we take patterns and ideas, never copy a specific shot or app's look. Don't scrape these sites (it's against their terms). Collect references by hand.

## How to add a reference

1. Save a screenshot to `docs/design/references/` named after what it shows, e.g. `mobbin-grocery-list-swipe.png`.
2. Add a line below: link, and **what you like about it** (colour? layout? a single interaction?).

## References

<!-- - `references/example.png`: link. What I like: ... -->

## Constraints the design must respect

- Text contrast meets WCAG AA in light and dark mode, even with bright colours.
- Tap targets of at least 44pt, and usable one-handed.
- Status colours (Confirmed / Estimated / Unknown, run out) must stay distinguishable from the brand colours.
- Everything goes through design tokens (`apps/client/src/theme/tokens.ts`). No hard-coded colours in screens.
