import { Loading, Screen } from '@/components/ui';
import { TodayBelow } from '@/features/home/TodayBelow';
import { TodayHero } from '@/features/home/TodayHero';
import { useMe } from '@/lib/api/households';
import { PageColors } from '@/theme/PageColors';

/** Home: tonight or the week, quick tiles and recipe ideas, on its blue page. */
export default function HomeScreen() {
  const me = useMe();
  return (
    <PageColors page="home">
      {/* The (app) layout only shows the tabs once you're in a Household, so data is there. */}
      {me.data ? (
        <Screen hero={<TodayHero me={me.data} />}>
          <TodayBelow />
        </Screen>
      ) : (
        <Loading />
      )}
    </PageColors>
  );
}
