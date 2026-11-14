import { useAuth } from '@clerk/expo';
import { Redirect, Slot } from 'expo-router';

import { Loading } from '@/components/ui';

/**
 * Signed-in screens. This check is for the user experience only: it decides which
 * screen to show. The real protection is the API, which rejects any request without
 * a valid token no matter what the app does.
 */
export default function AppLayout() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <Loading />;
  if (!isSignedIn) return <Redirect href="/sign-in" />;
  return <Slot />;
}
