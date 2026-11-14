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
