import { AllRecipesScreen } from '@/features/recipes/AllRecipesScreen';
import { PageColors } from '@/theme/PageColors';

/** Every recipe, from the Recipes screen's See all and chips (slice 6f), on the Recipes purple. */
export default function AllRecipesRoute() {
  return (
    <PageColors page="recipes" header>
      <AllRecipesScreen />
    </PageColors>
  );
}
