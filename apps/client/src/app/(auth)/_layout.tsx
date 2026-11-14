import { useAuth } from '@clerk/expo';
import { Redirect } from 'expo-router';
import { Stack } from 'expo-router/stack';

import { Loading } from '@/components/ui';
import { useTheme } from '@/theme/useTheme';

/**
 * Signed-out screens: welcome → how it works → sign in. Anyone already signed in is
 * sent to the app.
 *
 * A Stack (not a plain Slot) so moving between them slides like the rest of the app,
 * and Back works. The Stack also gives each screen its "main" landmark.
 */
export default function AuthLayout() {
  const t = useTheme();
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  if (isSignedIn) return <Redirect href="/" />;
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: t.colors.background },
      }}
    >
      <Stack.Screen name="welcome" options={{ title: 'Welcome to Sweep', animation: 'fade' }} />
      <Stack.Screen name="how-it-works" options={{ title: 'How Sweep works' }} />
      <Stack.Screen name="sign-in" options={{ title: 'Sign in' }} />
    </Stack>
  );
}
