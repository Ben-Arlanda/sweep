import { Loading, Screen } from '@/components/ui';
import { TodayBelow } from '@/features/home/TodayBelow';
import { TodayHero } from '@/features/home/TodayHero';
import { useMe } from '@/lib/api/households';

/** Home "Today" (slice 6c): tonight's dinner or the question, then the week and the list. */
export default function HomeScreen() {
  const me = useMe();
  // The (app) layout only shows the tabs once you're in a Household, so data is there.
  if (!me.data) return <Loading />;
  return (
    <Screen hero={<TodayHero me={me.data} />}>
      <TodayBelow />
    </Screen>
  );
}
