import { useAuth } from '@clerk/expo';
import { Redirect, Slot } from 'expo-router';

import { Loading } from '@/components/ui';

/** Signed-out screens. Anyone already signed in is sent to the app. */
export default function AuthLayout() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  if (isSignedIn) return <Redirect href="/" />;
  return <Slot />;
}
