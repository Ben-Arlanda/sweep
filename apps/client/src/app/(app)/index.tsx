import { useUser } from '@clerk/expo';

import { Button, ErrorText, Loading, Screen } from '@/components/ui';
import { HouseholdView } from '@/features/household/HouseholdView';
import { Onboarding } from '@/features/household/Onboarding';
import { useMe } from '@/lib/api/households';

export default function HomeScreen() {
  const { user } = useUser();
  const me = useMe();

  if (me.isPending) return <Loading />;

  if (me.isError) {
    return (
      <Screen>
        <ErrorText message={me.error.message} />
        <Button title="Try again" onPress={() => me.refetch()} />
      </Screen>
    );
  }

  const emailName = user?.primaryEmailAddress?.emailAddress.split('@')[0] ?? '';

  return (
    <Screen edges={['top', 'bottom', 'left', 'right']}>
      {me.data ? <HouseholdView me={me.data} /> : <Onboarding suggestedName={emailName} />}
    </Screen>
  );
}
