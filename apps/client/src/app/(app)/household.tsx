import { Loading, Screen } from '@/components/ui';
import { HouseholdSettings } from '@/features/household/HouseholdSettings';
import { useMe } from '@/lib/api/households';
import { PageColors } from '@/theme/PageColors';

/** Household settings (Members, invites, account), opened from Home's cog. */
function HouseholdContent() {
  const me = useMe();
  if (!me.data) return <Loading />;
  return (
    <Screen edges={['left', 'right', 'bottom']}>
      <HouseholdSettings me={me.data} />
    </Screen>
  );
}

/** Household settings, header bar included. */
export default function HouseholdScreen() {
  return (
    <PageColors page="household" header>
      <HouseholdContent />
    </PageColors>
  );
}
