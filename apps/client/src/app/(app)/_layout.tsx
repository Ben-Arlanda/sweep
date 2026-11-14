import { useAuth, useUser } from '@clerk/expo';
import { useIsRestoring, useQueryClient } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useEffect } from 'react';

import { useStackScreenOptions } from '@/components/stackOptions';
import { ToastProvider } from '@/components/Toast';
import { Button, ErrorText, Loading, Screen } from '@/components/ui';
import { Onboarding } from '@/features/household/Onboarding';
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
  if (!isSignedIn) return <Redirect href="/welcome" />;
  return <SignedIn />;
}

function SignedIn() {
  const stackOptions = useStackScreenOptions();
  const { user } = useUser();
  const emailName = user?.primaryEmailAddress?.emailAddress.split('@')[0] ?? '';
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

  return <ToastProvider>{body()}</ToastProvider>;

  function body() {
    if (me.isPending) return <Loading />;
    if (me.isError) {
      return (
        <Screen edges={['top', 'bottom', 'left', 'right']}>
          <ErrorText message={me.error.message} />
          <Button title="Try again" onPress={() => me.refetch()} />
        </Screen>
      );
    }
    // Not in a Household yet: create or join one first. The tabs would all be empty.
    if (!me.data) {
      return (
        <Screen edges={['top', 'bottom', 'left', 'right']}>
          <Onboarding suggestedName={emailName} />
        </Screen>
      );
    }
    return (
      <Stack screenOptions={stackOptions}>
        {/* The tabs, each with its own Stack, so the tab bar stays as you go deeper. */}
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="design" options={{ title: 'Design system' }} />
      </Stack>
    );
  }
}
