import { useIsFocused } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import type { ReactNode } from 'react';

import { PAGE_COLORS, palette, type Page } from './tokens';
import { ColorOverride } from './useTheme';

/**
 * Gives a main screen its page colour (PAGE_COLORS): everything inside, sheets too, gets
 * that page and its warm white cards. While the screen shows, the clock and battery icons
 * turn light on the darker pages.
 */
export function PageColors({ page, children }: { page: Page; children: ReactNode }) {
  const focused = useIsFocused();
  const colors = PAGE_COLORS[page];
  return (
    <ColorOverride.Provider value={colors}>
      {focused ? (
        <StatusBar style={colors.onBackground === palette.white ? 'light' : 'dark'} />
      ) : null}
      {children}
    </ColorOverride.Provider>
  );
}
