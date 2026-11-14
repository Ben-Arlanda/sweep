import {
  BricolageGrotesque_700Bold,
  BricolageGrotesque_800ExtraBold,
} from '@expo-google-fonts/bricolage-grotesque';
import { DMSans_400Regular, DMSans_500Medium, DMSans_700Bold } from '@expo-google-fonts/dm-sans';
import { ClerkProvider, useAuth } from '@clerk/expo';
import { tokenCache } from '@clerk/expo/token-cache';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { useFonts } from 'expo-font';
import { Slot } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useState, type ReactNode } from 'react';

import { setTokenGetter } from '@/lib/api/client';
import { CLERK_PUBLISHABLE_KEY } from '@/lib/config';
import { CACHE_BUSTER, CACHE_MAX_AGE, makeQueryClient, persister } from '@/lib/queryClient';

// Keep the splash screen up until the brand fonts are ready, so text never flashes
// in the system font and then jumps.
void SplashScreen.preventAutoHideAsync();

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Set EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY in apps/client/.env.local');
}

/**
 * The root of the app. Providers make shared things available to every screen below:
 * - ClerkProvider: who is signed in, plus their session token. `tokenCache` keeps the
 *   session in the device's encrypted storage (Keychain on iOS) so you stay signed in
 *   after closing the app. On web it's undefined and Clerk uses cookies instead.
 * - PersistQueryClientProvider: the cache of server data (lib/queryClient.ts), saved to
 *   device storage along with any changes still waiting to be sent.
 */
export default function RootLayout() {
  // useState so the cache is created once, not on every render.
  const [queryClient] = useState(makeQueryClient);
  const [fontsLoaded, fontError] = useFonts({
    BricolageGrotesque_700Bold,
    BricolageGrotesque_800ExtraBold,
    DMSans_400Regular,
    DMSans_500Medium,
    DMSans_700Bold,
  });
  const ready = fontsLoaded || Boolean(fontError); // on a font error, carry on with system fonts

  useEffect(() => {
    if (ready) void SplashScreen.hideAsync();
  }, [ready]);

  if (!ready) return null;

  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY} tokenCache={tokenCache}>
      <TokenBridge>
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{
            persister,
            buster: CACHE_BUSTER,
            maxAge: CACHE_MAX_AGE,
          }}
        >
          <Slot />
        </PersistQueryClientProvider>
      </TokenBridge>
    </ClerkProvider>
  );
}

/**
 * Hands Clerk's getToken to the API client (which lives outside React).
 *
 * Done during render, not in an effect, on purpose: React runs children's effects
 * before their parent's, so screens would start fetching before an effect here ran.
 * Assigning the same function again on each render is harmless.
 */
function TokenBridge({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  setTokenGetter(() => getToken());
  return children;
}
