import { Stack } from 'expo-router/stack';

import { useStackScreenOptions } from '@/components/stackOptions';

/** The Lists tab: all Shopping Lists, then one list. */
export default function ListsLayout() {
  return (
    <Stack screenOptions={useStackScreenOptions()}>
      <Stack.Screen name="index" options={{ title: 'Lists', headerShown: false }} />
      <Stack.Screen name="[id]" options={{ title: '' }} />
    </Stack>
  );
}
