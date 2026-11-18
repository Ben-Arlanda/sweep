import { View } from 'react-native';

import { Loading, Screen, Text } from '@/components/ui';
import { HouseholdSettings } from '@/features/household/HouseholdSettings';
import { useHousehold, useMe } from '@/lib/api/households';

/** Household settings (Members, invites, appearance, account), opened from Home's cog. */
export default function HouseholdScreen() {
  const me = useMe();
  const household = useHousehold(true);
  if (!me.data) return <Loading />;
  const count = household.data?.members.length;
  return (
    <Screen edges={['left', 'right', 'bottom']}>
      <View>
        <Text variant="title" role="heading" aria-level={2}>
          {me.data.household.name}
        </Text>
        {count === undefined ? null : (
          <Text muted>
            {me.data.member.display_name} · {count} {count === 1 ? 'Member' : 'Members'}
          </Text>
        )}
      </View>
      <HouseholdSettings me={me.data} />
    </Screen>
  );
}
