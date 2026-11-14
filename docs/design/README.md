# Design direction

Status: **Zest + Kitchen Table** chosen 2026-11-14, with matched-tint pills. Built in slice 3b; the rules are in [ADR 0007](../adr/0007-design-system-zest-kitchen-table.md), and you can browse them at `/design` in a development build.

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

Screenshots live in `references/` **on your machine only**. They're git-ignored because this repo is public and they're other people's work. The notes below are the record.

| File | Source | What we take from it |
|---|---|---|
| 01-greenso-product-detail | Greenso concept | White sheet rising over a sage photo area, nutrient fact chips, pill stepper with a deep-green CTA |
| 02–07 freshora-* | Freshora (Behance case study, store listing, marketing page) | Lime-to-yellow gradients, black price/quantity pills, cut-out food photography, soft radial glows, highlighter-marked words, phone-in-hand and dark-glow marketing shots |
| 08-placify-onboarding | Placify (Mobbin) | Tilted cards drifting and blurring in depth, words each in their own colour with a hand-drawn icon |
| 09–10 magnet-* | Magnet (Mobbin) | Shared group board, chunky rounded headings, coral accent, pastel colour per card, bottom sheet, avatars showing who's there |

Animation is part of the brief: the motion should feel springy and alive, and respect "reduce motion".

Directions drafted from these (Zest, Market Garden, Kitchen Table) are in the design-directions page shared on 2026-11-14. **Chosen:** Zest's lime and ink as the brand, with Kitchen Table's pastels and "who ticked it" personality inside the app. Quantity pills use matched tint (option 3 of 8).

## Constraints the design must respect

- Text contrast meets WCAG AA in light and dark mode, even with bright colours.
- Tap targets of at least 44pt, and usable one-handed.
- Status colours (Confirmed / Estimated / Unknown, run out) must stay distinguishable from the brand colours.
- Everything goes through design tokens (`apps/client/src/theme/tokens.ts`). No hard-coded colours in screens.
