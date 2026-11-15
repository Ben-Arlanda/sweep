import { Stack } from 'expo-router/stack';

import { useStackScreenOptions } from '@/components/stackOptions';

/** The Lists tab: the Household's one Shopping List (ADR 0009). */
export default function ListsLayout() {
  return (
    <Stack screenOptions={useStackScreenOptions()}>
      <Stack.Screen name="index" options={{ title: 'Shopping List', headerShown: false }} />
    </Stack>
  );
}
