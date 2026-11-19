import { createContext, useContext } from 'react';

import {
  colors,
  fonts,
  motion,
  radius,
  shadow,
  space,
  statusColors,
  stockColors,
  tints,
  touchTarget,
  type,
  type ColorTokens,
} from './tokens';

/** Always light: dark mode was removed (2026-11-18). Kept as a hook so callers don't change. */
export function useScheme(): 'light' | 'dark' {
  return 'light';
}

/** Colours a screen swaps in for everything inside it (PAGE_COLORS). */
export const ColorOverride = createContext<Partial<ColorTokens> | null>(null);

/** The current theme. Re-renders automatically when the scheme changes. */
export function useTheme() {
  const scheme = useScheme();
  const override = useContext(ColorOverride);
  return {
    scheme,
    colors: override ? { ...colors[scheme], ...override } : colors[scheme],
    tints: tints[scheme],
    status: statusColors[scheme],
    stock: stockColors[scheme],
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
