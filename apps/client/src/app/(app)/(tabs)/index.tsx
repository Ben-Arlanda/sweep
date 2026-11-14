import { Loading, Screen } from '@/components/ui';
import { HomeHero, HouseholdView } from '@/features/household/HouseholdView';
import { useMe } from '@/lib/api/households';

/** Home: the Household hero, then the board of tiles (lists, Cabinet, Recipes). */
export default function HomeScreen() {
  const me = useMe();
  // The (app) layout only shows the tabs once you're in a Household, so data is there.
  if (!me.data) return <Loading />;
  return (
    <Screen hero={<HomeHero me={me.data} />}>
      <HouseholdView />
    </Screen>
  );
}
