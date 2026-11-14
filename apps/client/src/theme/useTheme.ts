import { useColorScheme } from 'react-native';

import {
  colors,
  fonts,
  motion,
  radius,
  shadow,
  space,
  statusColors,
  tints,
  touchTarget,
  type,
} from './tokens';

/** The current theme. Re-renders automatically when the device switches light/dark. */
export function useTheme() {
  const scheme = useColorScheme() === 'dark' ? 'dark' : 'light';
  return {
    scheme,
    colors: colors[scheme],
    tints: tints[scheme],
    status: statusColors[scheme],
    fonts,
    space,
    radius,
    type,
    shadow,
    motion,
    touchTarget,
  };
}

export type Theme = ReturnType<typeof useTheme>;
