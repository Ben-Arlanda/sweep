import { useIsFocused } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { Loading, Screen } from '@/components/ui';
import { TodayBelow } from '@/features/home/TodayBelow';
import { TodayHero } from '@/features/home/TodayHero';
import { useMe } from '@/lib/api/households';
import { homeColors } from '@/theme/tokens';
import { ColorOverride } from '@/theme/useTheme';

/**
 * Home: tonight or the week, quick tiles and recipe ideas. Home has its own colours
 * (`homeColors`): a blue page, no coloured hero, warm white cards. Light clock and
 * battery icons on the blue while Home is showing.
 */
export default function HomeScreen() {
  const me = useMe();
  const focused = useIsFocused();
  return (
    <ColorOverride.Provider value={homeColors}>
      {focused ? <StatusBar style="light" /> : null}
      {/* The (app) layout only shows the tabs once you're in a Household, so data is there. */}
      {me.data ? (
        <Screen hero={<TodayHero me={me.data} />}>
          <TodayBelow />
        </Screen>
      ) : (
        <Loading />
      )}
    </ColorOverride.Provider>
  );
}
