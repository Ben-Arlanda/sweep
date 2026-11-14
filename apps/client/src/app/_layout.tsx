import { ClerkProvider } from '@clerk/expo';
import { tokenCache } from '@clerk/expo/token-cache';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Slot } from 'expo-router';
import { useState } from 'react';

import { CLERK_PUBLISHABLE_KEY } from '@/lib/config';

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY in apps/client/.env.local');
}

/**
 * The root of the app. Providers make shared things available to every screen below:
 * - ClerkProvider: who is signed in, plus their session token. `tokenCache` keeps the
 *   session in the device's encrypted storage (Keychain on iOS) so you stay signed in
 *   after closing the app. On web it's undefined and Clerk uses cookies instead.
 * - QueryClientProvider: the cache of server data (see lib/api/households.ts).
 */
export default function RootLayout() {
  // useState so the cache is created once, not on every render.
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } }),
  );

  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY} tokenCache={tokenCache}>
      <QueryClientProvider client={queryClient}>
        <Slot />
      </QueryClientProvider>
    </ClerkProvider>
  );
}
