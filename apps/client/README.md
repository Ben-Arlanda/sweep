# Sweep client

Expo app for iOS, web and Android (Expo Router, TypeScript). Routes live in `src/app/`.

```bash
npm install
npx expo start      # w = web, scan the QR code with Expo Go on iPhone
npm run typecheck
npm run lint
npm test            # Jest (jest-expo)
```

Add packages with `npx expo install <pkg>` (not `npm install`) so versions match the Expo SDK.
See `AGENTS.md` for Expo-specific rules.

## Design system and accessibility

The look ("Zest + Kitchen Table") and its rules are in [ADR 0007](../../docs/adr/0007-design-system-zest-kitchen-table.md).

- Build screens from `src/components/`, and take every colour, font, space and motion value from `useTheme()`. Never hard-code a colour.
- Lime (`colors.action`) is for actions only, never for text. Give lists, people and items a pastel with `tintFor(id)`.
- `src/theme/tokens.test.ts` checks WCAG AA contrast for every colour pair, so adding a colour that fails will fail CI.
- Open `/design` (linked from Account in development builds) to see every component in the current theme. Check it in dark mode and with Reduce Motion on.
- Before merging UI, run a Lighthouse accessibility audit on the screens you changed (aim for 100), in light and dark mode.

## Clerk (sign-in)

1. Copy `.env.example` values into `apps/client/.env.local`, including `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` (Clerk Dashboard → API keys). It's public; the **secret** key never goes in the client.
2. In the Clerk Dashboard → User & authentication: turn **Password off**, use **Email verification code** for sign-up and sign-in, and turn on **Allow users to delete their accounts**.
3. For Expo Go on a phone: enable the **Native API** (Dashboard → Native applications), and set `EXPO_PUBLIC_API_URL` to your Mac's LAN IP, because `localhost` on a phone is the phone itself.

Test sign-ins: `anything+clerk_test@example.com` with code `424242` (development instances only).

## API types

`npm run api:types` regenerates `src/lib/api/schema.ts` from the FastAPI schema. Run it after any backend endpoint change.

## Shared lists: how sync works

- **Reads** go through TanStack Query (`src/lib/api/lists.ts`). **Writes** are mutations registered once with `setMutationDefaults`, so a change queued before an app restart can still run.
- Each change gets its `Idempotency-Key` (and a new item gets its id) **when the Member taps**. Retries reuse both, so the server applies each change once.
- Changes to one list share a mutation `scope`, so they're sent in order. Offline, they pause and are saved to storage. The screen updates straight away (optimistic) and shows "Offline. N changes will sync".
- `useChangeNotices` keeps a WebSocket to `/ws`. A notice says "list X is at version N", and the app refetches that list if its copy is older (ADR 0004).
- Known gap: a change that was **in flight** (not paused) when the app was killed isn't saved. TanStack only saves paused mutations.

## Cabinet

`src/lib/api/cabinet.ts` follows the same pattern: changes are queued, idempotent and not optimistic. The server decides units and status (ADR 0003), and the app only formats them (`features/cabinet/format.ts`). A tick on a list item linked to an Ingredient also refetches the Cabinet. Cabinet change notices arrive as `entity: "cabinet"`.

Dev server tip: run `npx expo start` normally. With `CI=1`, Metro doesn't watch files, so new screens and edits never appear.
