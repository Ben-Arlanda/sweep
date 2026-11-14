/**
 * The app's server-data cache, set up for flaky supermarket signal.
 *
 * - onlineManager + NetInfo: on iOS/Android, TanStack can't see the network by itself
 *   (browsers have `navigator.onLine`, phones don't). NetInfo tells it, so mutations
 *   pause while offline and resume when the signal comes back.
 * - Persister: saves the cache and any paused mutations to device storage
 *   (AsyncStorage; localStorage on web). Close the app with unsent ticks, reopen it,
 *   and they're still queued.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { onlineManager, QueryClient } from '@tanstack/react-query';
import { Platform } from 'react-native';

import { registerListMutations } from '@/lib/api/lists';

if (Platform.OS !== 'web') {
  onlineManager.setEventListener((setOnline) =>
    NetInfo.addEventListener((state) => setOnline(state.isConnected !== false)),
  );
}

const DAY = 24 * 60 * 60 * 1000;

export function makeQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      // gcTime must be at least the persister's maxAge, or restored data is thrown away.
      queries: { retry: 1, staleTime: 30_000, gcTime: DAY },
    },
  });
  registerListMutations(queryClient);
  return queryClient;
}

export const persister = createAsyncStoragePersister({ storage: AsyncStorage });

/** Bump when cached shapes change, so old caches aren't restored into new code. */
export const CACHE_BUSTER = 'slice-2';
export const CACHE_MAX_AGE = DAY;
