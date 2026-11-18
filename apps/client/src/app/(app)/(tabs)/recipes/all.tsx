import { Stack } from 'expo-router';

import { AllRecipesScreen } from '@/features/recipes/AllRecipesScreen';
import { PageColors } from '@/theme/PageColors';
import { useTheme } from '@/theme/useTheme';

/** Every recipe, from the Recipes screen's See all and chips (slice 6f), on the Recipes purple. */
export default function AllRecipesRoute() {
  return (
    <PageColors page="recipes">
      <PageHeaderBar />
      <AllRecipesScreen />
    </PageColors>
  );
}

/** The header bar above the screen matches its page: purple, with white title and Back. */
function PageHeaderBar() {
  const t = useTheme();
  return (
    <Stack.Screen
      options={{
        headerStyle: { backgroundColor: t.colors.background },
        headerTintColor: t.colors.onBackground,
        contentStyle: { backgroundColor: t.colors.background },
      }}
    />
  );
}
