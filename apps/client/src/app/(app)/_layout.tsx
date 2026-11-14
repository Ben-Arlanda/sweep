import { useAuth } from '@clerk/expo';
import { useIsRestoring, useQueryClient } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { useEffect } from 'react';

import { ToastProvider } from '@/components/Toast';
import { Loading } from '@/components/ui';
import { useMe } from '@/lib/api/households';
import { useChangeNotices } from '@/lib/sync/useChangeNotices';
import { useTheme } from '@/theme/useTheme';

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
  const t = useTheme();
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
    <ToastProvider>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: t.colors.background },
          headerShadowVisible: false,
          headerTintColor: t.colors.text,
          headerTitleStyle: { fontFamily: t.fonts.displayBold, fontSize: 18 },
          headerBackButtonDisplayMode: 'minimal',
          contentStyle: { backgroundColor: t.colors.background },
        }}
      >
        {/* Home draws its own header (Household chip and avatars). */}
        <Stack.Screen name="index" options={{ title: 'Home', headerShown: false }} />
        <Stack.Screen name="lists/[id]" options={{ title: '' }} />
        <Stack.Screen name="cabinet" options={{ title: '' }} />
        <Stack.Screen name="design" options={{ title: 'Design system' }} />
      </Stack>
    </ToastProvider>
  );
}
