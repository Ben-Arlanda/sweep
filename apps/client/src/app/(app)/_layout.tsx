import { useAuth } from '@clerk/expo';
import { useIsRestoring, useQueryClient } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useEffect } from 'react';

import { Loading } from '@/components/ui';
import { useMe } from '@/lib/api/households';
import { useChangeNotices } from '@/lib/sync/useChangeNotices';

/**
 * Signed-in screens. This check is for the user experience only: it decides which
 * screen to show. The real protection is the API, which rejects any request without
 * a valid token no matter what the app does.
 */
export default function AppLayout() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  if (!isSignedIn) return <Redirect href="/sign-in" />;
  return <SignedIn />;
}

function SignedIn() {
  const queryClient = useQueryClient();
  const isRestoring = useIsRestoring();
  const me = useMe();
  const inHousehold = Boolean(me.data);

  // Changes queued in an earlier session come back from storage paused. Send them once
  // both the restore has finished and Clerk can give us a token (we're inside the
  // signed-in branch); any earlier and they'd fail with 401.
  useEffect(() => {
    if (!isRestoring) void queryClient.resumePausedMutations();
  }, [isRestoring, queryClient]);

  useChangeNotices(inHousehold);

  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: 'Sweep' }} />
      <Stack.Screen name="lists/[id]" options={{ title: 'Shopping List' }} />
      <Stack.Screen name="cabinet" options={{ title: 'Cabinet' }} />
    </Stack>
  );
}
