import { useColorScheme } from 'react-native';

import { colors, radius, space, touchTarget, type } from './tokens';

/** The current theme. Re-renders automatically when the device switches light/dark. */
export function useTheme() {
  const scheme = useColorScheme() === 'dark' ? 'dark' : 'light';
  return { scheme, colors: colors[scheme], space, radius, type, touchTarget };
}

export type Theme = ReturnType<typeof useTheme>;
