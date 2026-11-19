import { Loading, Screen } from '@/components/ui';
import { TodayBelow } from '@/features/home/TodayBelow';
import { TodayHero, usePlanFlow } from '@/features/home/TodayHero';
import type { MeOut } from '@/lib/api/client';
import { useMe } from '@/lib/api/households';
import { PageColors } from '@/theme/PageColors';

/** Home: tonight or the week, quick tiles and recipe ideas. */
export default function HomeScreen() {
  const me = useMe();
  return (
    <PageColors page="home">
      {/* The (app) layout only shows the tabs once you're in a Household, so data is there. */}
      {me.data ? <Home me={me.data} /> : <Loading />}
    </PageColors>
  );
}

function Home({ me }: { me: MeOut }) {
  const flow = usePlanFlow();
  return (
    <Screen hero={<TodayHero me={me} flow={flow} />}>
      <TodayBelow onEditPlan={flow.edit} />
    </Screen>
  );
}
