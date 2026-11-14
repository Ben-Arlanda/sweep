import { Hero, HeroLabel } from '@/components/Hero';
import { Loading, Screen } from '@/components/ui';
import { HouseholdSettings } from '@/features/household/HouseholdView';
import { useHousehold, useMe } from '@/lib/api/households';

/** The Household tab: Members, invites, appearance and account. */
export default function HouseholdScreen() {
  const me = useMe();
  const household = useHousehold(true);
  // The (app) layout only shows the tabs once you're in a Household, so data is there.
  if (!me.data) return <Loading />;
  const count = household.data?.members.length;
  return (
    <Screen
      hero={
        <Hero
          top={<HeroLabel label="You" value={me.data.member.display_name} />}
          title={me.data.household.name}
          subtitle={
            count === undefined ? undefined : `${count} ${count === 1 ? 'Member' : 'Members'}`
          }
        />
      }
    >
      <HouseholdSettings me={me.data} />
    </Screen>
  );
}
