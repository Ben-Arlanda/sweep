# 7. A small, code-first design system: "Zest + Kitchen Table"

Date: 2026-11-14 · Status: Accepted

## Context

Sweep is for public release and must look premium, colourful and bright enough to stand out. It also needs to explain the product (the shop, Cabinet, cook, plan loop) and feel like one business across the app, the web and marketing. Screens get built over many weeks, often in separate sessions, so without shared rules they drift apart. Accessibility (WCAG 2.2 AA) is a requirement, not a later pass.

Three directions were compared with interactive mock-ups (Zest, Market Garden, Kitchen Table; references are in `docs/design/README.md`). The product owner chose a blend of Zest and Kitchen Table, with "matched tint" quantity pills.

## Decision

A **code-first** design system inside the client. There's no Figma library or Storybook while the team is one developer.

- **Tokens** (`apps/client/src/theme/tokens.ts`) hold colour *roles*, not raw colours, plus fonts, a type scale, spacing, radius, shadows and motion. Every component and screen reads from them.
- **Colour has jobs:**
  - Lime is for *actions only* (primary buttons, ticks, the AI). It's never used for text on a light background (about 1.3:1 contrast).
  - Ink and white are for reading.
  - Warm white is the background.
  - Five pastels (butter, blush, mint, sky, lilac) give each list, Member and item its own colour, picked by a stable hash of its id (`tintFor`), so Bob is the same colour on every phone.
  - Quantity pills use a deeper shade of the item's own pastel ("matched tint").
  - Cabinet statuses (Confirmed, Estimated, Unknown, Run out) have their own colours, and Unknown is dashed, so a status is never shown by colour alone and never mistaken for an action.
- **Food thumbnails:** every food item and recipe shows a food emoji on its own pastel square (`FoodThumb`). The emoji are chosen in the app (`theme/foodEmoji.ts`), like the tints: every Ingredient has one, with a category fallback, and recipes get one from words in their title. A test reads the API's Ingredient list and Seed Recipes and fails if any lacks a specific emoji. Only emoji from Unicode 13 (2020) or earlier, so older phones don't show empty boxes. Real food photos can replace them later without changing screens. *(Added 2026-11-14.)*
- **Type:** Urbanist for everything: 700 for big headings, 600 for headings and labels, 500 for body text. It's a free, round geometric sans close to Gilroy (the font in the reference the user picked; Gilroy needs a paid licence). *(Changed 2026-11-14; was Bricolage Grotesque + DM Sans.)* Each weight is its own font family, because on Android a custom family plus `fontWeight` can fall back to the system font.
- **Motion** (Reanimated 4, on the UI thread): one springy feel.
  - Buttons shrink slightly while pressed.
  - Ticks "pop" (only on a change, never on first render).
  - Rows rise in one after another.
  - A toast confirms "Added to Cabinet", which shows the loop working.
  - Everything respects the device's Reduce Motion setting.
- **Welcome and "how it works"** (signed-out only, before sign-in): an always-ink hero with a lime glow, drifting tilted cards and the website headline, then four swipeable pages (shop, Cabinet, ask, plan) drawn with the real components. Pages about features that aren't built yet say "Coming soon". The words live in `features/welcome/story.ts`. *(Added 2026-11-14.)*
- **Dark by default** (`theme/appearance.ts`): the app starts dark whatever the phone is set to. Household → Appearance offers Dark, Light or Match my phone, saved on the device. Both themes keep the same contrast tests. *(Added 2026-11-14.)*
- **Tab bar** along the bottom (`app/(app)/(tabs)`): Home, Lists, Cabinet, Recipes, Household, each an icon plus a word. Each tab has its own Stack, so the bar stays while you open a list or a recipe. The selected tab fills its icon, sits on a lime pill and bolds its label, so it never relies on colour alone. Icons are Material Community Icons from `@expo/vector-icons`, so they look the same on iPhone, Android and the web. *(Added 2026-11-14.)*
- **Hero** (`components/Hero.tsx`): the main tab screens open with a dark panel that runs up under the status bar and has big rounded bottom corners (32pt), holding the title and, where there is one, the search box. Pale lime on the light theme; on the dark theme a lighter green-grey, so it still stands out from the page. *(Light theme changed from ink to pale lime at the user's request, 2026-11-14.)* Detail screens (one list, one recipe) keep their pastel summary card instead. *(Added 2026-11-14.)*
- **Components** live in `src/components/`: Text, Highlight, Screen, Card, Button, Field, Pill, Tag, StatusBadge, Avatar, AvatarStack, Checkbox, Toast, Tile, PressableScale. A dev-only `/design` screen shows every one in the current theme.

## Accessibility rules (WCAG 2.2 AA)

- **Contrast is tested, not eyeballed:** `tokens.test.ts` checks every text and background pair, tint pill and status badge against 4.5:1 in light and dark mode. A new colour that fails, fails CI.
- **Tap targets** are at least 44pt. List rows are 56pt, and the whole row is the checkbox.
- **The accessible name contains the visible text** (2.5.3 Label in Name): rows and tiles take their name from what's on screen, and a custom label is used only to *add* context ("Remove Bob from the Household").
- **States are exposed:** checkboxes set `aria-checked`, and loading buttons keep their name while the spinner shows.
- **Decorative things are hidden:** avatar initials, thumbnails, emoji and the ✓ glyph use `aria-hidden`, so screen readers don't read "A" or "check mark".
- **Toasts are polite**, not "alert": they're announced without interrupting.
- **No opacity for "done":** dimming a ticked row would push its captions below AA contrast. Strike-through, the tick and the muted name show the state instead.
- **Layout and focus:** every screen has a `main` landmark and one heading. Text scales with the system font size, and layouts reflow at 320px wide with no sideways scrolling. Keyboard focus is visible on web.
- **Checks before merging UI:** run Lighthouse accessibility (target 100) on the changed screens in light and dark mode, and use the VoiceOver rotor on a phone when one is available.

## Consequences

- New screens are put together from the components, and a hard-coded colour or font in a screen is a review smell.
- Dark mode comes almost free, because roles have two values. The pastels needed hand-picked dark versions.
- The marketing website (later) should reuse the same tokens, probably by moving `tokens.ts` into a shared package when that site exists. Not before.
- App icon and splash artwork aren't designed yet. The splash background now uses the brand colours.
