import { useAuth } from '@clerk/expo';
import { Redirect, Slot } from 'expo-router';
import { View } from 'react-native';

import { Loading } from '@/components/ui';

/** Signed-out screens. Anyone already signed in is sent to the app. */
export default function AuthLayout() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  if (isSignedIn) return <Redirect href="/" />;
  // The signed-in screens get a "main" landmark from the navigation stack; this area has
  // no stack, so we add it ourselves. Screen readers use it to jump straight to content.
  return (
    <View role="main" style={{ flex: 1 }}>
      <Slot />
    </View>
  );
}
