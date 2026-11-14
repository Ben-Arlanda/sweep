import { useColorScheme } from 'react-native';

import { useAppearance } from './appearance';
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

/** Light or dark, from the person's Appearance choice (dark unless they changed it). */
export function useScheme(): 'light' | 'dark' {
  const appearance = useAppearance();
  const phone = useColorScheme(); // only used when they chose "match my phone"
  if (appearance === 'system') return phone === 'light' ? 'light' : 'dark';
  return appearance;
}

/** The current theme. Re-renders automatically when the scheme changes. */
export function useTheme() {
  const scheme = useScheme();
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
