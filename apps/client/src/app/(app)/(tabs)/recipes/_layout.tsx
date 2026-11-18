import { Stack } from 'expo-router/stack';

import { useStackScreenOptions } from '@/components/stackOptions';

/** A link straight to one recipe still puts the directory underneath it. */
export const unstable_settings = { initialRouteName: 'index' };

/** The Recipes tab: browse and search, then one recipe; adding or editing your own. */
export default function RecipesLayout() {
  return (
    <Stack screenOptions={useStackScreenOptions()}>
      <Stack.Screen name="index" options={{ title: 'Recipes', headerShown: false }} />
      <Stack.Screen name="[id]" options={{ title: '' }} />
      <Stack.Screen name="review" options={{ title: '' }} />
    </Stack>
  );
}
