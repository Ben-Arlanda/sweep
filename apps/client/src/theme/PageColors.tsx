import { Stack, useIsFocused } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { ReactNode } from 'react';

import { PAGE_COLORS, type Page } from './tokens';
import { ColorOverride } from './useTheme';

/**
 * Gives a screen its page colour (PAGE_COLORS): everything inside, sheets too, gets that
 * page and its white cards. Every page is light now, so the status bar icons stay dark. `header`: a screen with a header bar (Back and a title)
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
        <StatusBar style="dark" />
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
