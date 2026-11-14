/**
 * Design tokens: the app's shared visual decisions, named once and used everywhere.
 *
 * Components never hard-code a colour or a spacing value. They ask for a token
 * ("primary", "space.md"), so changing the look means changing this file only,
 * and light/dark mode is just a second set of values for the same names.
 */

const palette = {
  basil700: '#245740',
  basil600: '#2f6b4f',
  basil300: '#7cc49f',
  basil100: '#e3efe7',
  ink900: '#1d2420',
  ink600: '#5b6760',
  ink300: '#c9d0c8',
  paper: '#f7f8f4',
  white: '#ffffff',
  night900: '#121714',
  night800: '#18201b',
  night600: '#2c3730',
  mist200: '#e4e9e4',
  mist400: '#9aa69e',
  tomato600: '#b3261e',
  tomato300: '#f2b8b5',
} as const;

export type ColorTokens = {
  background: string;
  surface: string;
  text: string;
  textMuted: string;
  border: string;
  primary: string;
  primaryPressed: string;
  onPrimary: string;
  primarySoft: string;
  danger: string;
};

export const colors: Record<'light' | 'dark', ColorTokens> = {
  light: {
    background: palette.paper,
    surface: palette.white,
    text: palette.ink900,
    textMuted: palette.ink600,
    border: palette.ink300,
    primary: palette.basil600,
    primaryPressed: palette.basil700,
    onPrimary: palette.white,
    primarySoft: palette.basil100,
    danger: palette.tomato600,
  },
  dark: {
    background: palette.night900,
    surface: palette.night800,
    text: palette.mist200,
    textMuted: palette.mist400,
    border: palette.night600,
    primary: palette.basil300,
    primaryPressed: palette.basil100,
    onPrimary: palette.night900,
    primarySoft: '#1d3127',
    danger: palette.tomato300,
  },
};

// A 4-point scale: every gap and padding is one of these, which keeps layouts even.
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 6, md: 10, lg: 16, pill: 999 } as const;

export const type = {
  title: { fontSize: 28, fontWeight: '700', lineHeight: 34 },
  heading: { fontSize: 20, fontWeight: '600', lineHeight: 26 },
  body: { fontSize: 16, fontWeight: '400', lineHeight: 22 },
  label: { fontSize: 14, fontWeight: '600', lineHeight: 18 },
  caption: { fontSize: 13, fontWeight: '400', lineHeight: 18 },
} as const;

// Minimum comfortable touch target (Apple's guideline is 44pt).
export const touchTarget = 44;
