import { Stack, useIsFocused } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { ReactNode } from 'react';

import { PAGE_COLORS, palette, type Page } from './tokens';
import { ColorOverride } from './useTheme';

/**
 * Gives a screen its page colour (PAGE_COLORS): everything inside, sheets too, gets that
 * page and its warm white cards. While the screen shows, the clock and battery icons turn
 * light on the darker pages. `header`: a screen with a header bar (Back and a title)
 * colours that bar to match, since the stack draws it outside the screen.
 */
export function PageColors({
  page,
  header = false,
  children,
}: {
  page: Page;
  header?: boolean;
  children: ReactNode;
}) {
  const focused = useIsFocused();
  const colors = PAGE_COLORS[page];
  return (
    <ColorOverride.Provider value={colors}>
      {focused ? (
        <StatusBar style={colors.onBackground === palette.white ? 'light' : 'dark'} />
      ) : null}
      {header ? (
        <Stack.Screen
          options={{
            headerStyle: { backgroundColor: colors.background },
            headerTintColor: colors.onBackground,
            contentStyle: { backgroundColor: colors.background },
          }}
        />
      ) : null}
      {children}
    </ColorOverride.Provider>
  );
}
