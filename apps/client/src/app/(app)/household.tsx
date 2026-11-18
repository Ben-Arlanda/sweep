import { View } from 'react-native';

import { Loading, Screen, Text } from '@/components/ui';
import { HouseholdSettings } from '@/features/household/HouseholdSettings';
import { useHousehold, useMe } from '@/lib/api/households';
import { PageColors } from '@/theme/PageColors';
import { useTheme } from '@/theme/useTheme';

/** Household settings (Members, invites, account), opened from Home's cog. */
function HouseholdContent() {
  const t = useTheme();
  const me = useMe();
  const household = useHousehold(true);
  if (!me.data) return <Loading />;
  const count = household.data?.members.length;
  return (
    <Screen edges={['left', 'right', 'bottom']}>
      <View>
        <Text
          variant="title"
          role="heading"
          aria-level={2}
          style={{ color: t.colors.onBackground }}
        >
          {me.data.household.name}
        </Text>
        {count === undefined ? null : (
          <Text style={{ color: t.colors.onBackgroundMuted }}>
            {me.data.member.display_name} · {count} {count === 1 ? 'Member' : 'Members'}
          </Text>
        )}
      </View>
      <HouseholdSettings me={me.data} />
    </Screen>
  );
}

/** Household settings on its navy page, header bar included. */
export default function HouseholdScreen() {
  return (
    <PageColors page="household" header>
      <HouseholdContent />
    </PageColors>
  );
}
