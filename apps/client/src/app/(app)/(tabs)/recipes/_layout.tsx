import { Stack } from 'expo-router/stack';

import { useStackScreenOptions } from '@/components/stackOptions';

/** The Recipes tab: browse and search, then one recipe. */
export default function RecipesLayout() {
  return (
    <Stack screenOptions={useStackScreenOptions()}>
      <Stack.Screen name="index" options={{ title: 'Recipes', headerShown: false }} />
      <Stack.Screen name="[id]" options={{ title: '' }} />
    </Stack>
  );
}
