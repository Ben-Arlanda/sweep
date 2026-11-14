import { View } from 'react-native';

import { Hero } from '@/components/Hero';
import { Screen } from '@/components/ui';
import { ListTiles, NewList } from '@/features/lists/ListTiles';
import { useTheme } from '@/theme/useTheme';

/** The Lists tab: every Shopping List in the Household, and a way to start a new one. */
export default function ListsScreen() {
  const t = useTheme();
  return (
    <Screen
      hero={
        <Hero
          title="Lists"
          subtitle="Shared with everyone in your Household. Tick things off as you shop."
        />
      }
    >
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.md }}>
        <ListTiles />
      </View>
      <NewList />
    </Screen>
  );
}
