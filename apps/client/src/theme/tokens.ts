/**
 * Design tokens: the app's shared visual decisions, named once and used everywhere.
 *
 * Direction: "Zest + Kitchen Table" (ADR 0007). Lime and ink are the brand; warm white
 * and soft pastels make it feel like a household kitchen rather than a shop.
 *
 * Components never hard-code a colour or a spacing value. They ask for a *role*
 * ("action", "textMuted", a tint) rather than a raw colour, so each colour has one job:
 * - Lime is for actions only (main buttons, ticks, the AI). Never text on white.
 * - Pastel tints give each list, Member and item its own colour. Quantity pills use a
 *   deeper shade of the same tint ("matched tint").
 * - Cabinet statuses have their own colours so they never get confused with the brand.
 *
 * Contrast for every text/background pair is checked in tokens.test.ts.
 */

const palette = {
  lime: '#d8f23c',
  limePressed: '#c5de25',
  limeSoft: '#eef8b8',
  ink: '#12150f',
  ink700: '#2a2f24',
  paper: '#fffaf4',
  white: '#ffffff',
  stone600: '#5d6155',
  stone300: '#e7e2d6',
  night900: '#0f110d',
  night800: '#181b15',
  night700: '#22261e',
  night600: '#2c3127',
  mist100: '#eef1e6',
  mist400: '#a6ab9b',
  red700: '#a3271a',
  red600: '#b3261e',
  red100: '#ffe1dc',
  red300: '#ffb4a8',
} as const;

export type ColorTokens = {
  background: string;
  surface: string;
  text: string;
  textMuted: string;
  border: string;
  /** Lime: main buttons, ticks, the AI. */
  action: string;
  actionPressed: string;
  onAction: string;
  actionSoft: string;
  onActionSoft: string;
  /** The one strong dark (light in dark mode) surface: toasts and anchor cards. */
  inverse: string;
  onInverse: string;
  danger: string;
  dangerSoft: string;
  /**
   * The rounded panel at the top of the main screens. Pale lime on the light theme; on
   * the dark theme a lighter green-grey, so it still stands out from the page.
   */
  hero: string;
  onHero: string;
  onHeroMuted: string;
  /** The search field inside the hero. */
  heroField: string;
};

export const colors: Record<'light' | 'dark', ColorTokens> = {
  light: {
    background: palette.paper,
    surface: palette.white,
    text: palette.ink,
    textMuted: palette.stone600,
    border: palette.stone300,
    action: palette.lime,
    actionPressed: palette.limePressed,
    onAction: palette.ink,
    actionSoft: palette.limeSoft,
    onActionSoft: '#2f3600',
    inverse: palette.ink,
    onInverse: palette.white,
    danger: palette.red600,
    dangerSoft: palette.red100,
    hero: palette.limeSoft,
    onHero: palette.ink,
    onHeroMuted: '#4d5338',
    heroField: palette.white,
  },
  dark: {
    background: palette.night900,
    surface: palette.night800,
    text: palette.mist100,
    textMuted: palette.mist400,
    border: palette.night600,
    action: palette.lime, // lime with ink text works on dark backgrounds too
    actionPressed: palette.limePressed,
    onAction: palette.ink,
    actionSoft: '#323a10',
    onActionSoft: '#e6f59a',
    inverse: palette.mist100,
    onInverse: palette.ink,
    danger: palette.red300,
    dangerSoft: '#4a1f19',
    hero: '#262b21',
    onHero: palette.mist100,
    onHeroMuted: '#bfc4b3',
    heroField: '#353b2e',
  },
};

/** The household pastels. `bg` for cards and thumbnails, `pill`/`onPill` for quantity pills. */
export const TINT_NAMES = ['butter', 'blush', 'mint', 'sky', 'lilac'] as const;
export type TintName = (typeof TINT_NAMES)[number];
export type Tint = { bg: string; pill: string; onPill: string; text: string };

export const tints: Record<'light' | 'dark', Record<TintName, Tint>> = {
  light: {
    butter: { bg: '#fde9a6', pill: '#f6d469', onPill: '#4a3500', text: palette.ink },
    blush: { bg: '#f9d6cf', pill: '#f4b9ab', onPill: '#5b1d12', text: palette.ink },
    mint: { bg: '#cdebd9', pill: '#9fd7b6', onPill: '#0f3d24', text: palette.ink },
    sky: { bg: '#d3e0fc', pill: '#aec5f6', onPill: '#13306b', text: palette.ink },
    lilac: { bg: '#ecdaf6', pill: '#d6b9ec', onPill: '#43195e', text: palette.ink },
  },
  dark: {
    butter: { bg: '#3a3218', pill: '#5a4b1c', onPill: '#fde9a6', text: palette.mist100 },
    blush: { bg: '#3a2420', pill: '#5c3329', onPill: '#f9d6cf', text: palette.mist100 },
    mint: { bg: '#1d3428', pill: '#2b4d3b', onPill: '#cdebd9', text: palette.mist100 },
    sky: { bg: '#1f2a44', pill: '#2f3f66', onPill: '#d3e0fc', text: palette.mist100 },
    lilac: { bg: '#33253d', pill: '#4a3758', onPill: '#ecdaf6', text: palette.mist100 },
  },
};

/** Cabinet statuses (ADR 0003), deliberately not lime so they never read as "tap me". */
export type StatusName = 'confirmed' | 'estimated' | 'unknown' | 'runOut';
export type StatusColors = { bg: string; fg: string; border: string };

export const statusColors: Record<'light' | 'dark', Record<StatusName, StatusColors>> = {
  light: {
    confirmed: { bg: '#e4ecff', fg: '#1f3f9e', border: '#e4ecff' },
    estimated: { bg: '#fff0c7', fg: '#6e4a00', border: '#fff0c7' },
    unknown: { bg: 'transparent', fg: '#545a4f', border: '#b3baa9' },
    runOut: { bg: palette.red100, fg: palette.red700, border: palette.red100 },
  },
  dark: {
    confirmed: { bg: '#1e2a4a', fg: '#c9d7ff', border: '#1e2a4a' },
    estimated: { bg: '#3a2f10', fg: '#ffd98a', border: '#3a2f10' },
    unknown: { bg: 'transparent', fg: '#b5bcab', border: '#5a6152' },
    runOut: { bg: '#4a1f19', fg: palette.red300, border: '#4a1f19' },
  },
};

/**
 * The welcome hero: always ink with a lime glow, in light and dark mode alike, like the
 * website hero. It's the one place the brand is shown "full volume".
 */
export const hero = {
  background: palette.ink,
  /**
   * A soft lime light behind the floating cards (a CSS radial gradient). It stays in the
   * top half on purpose: text sits on plain ink, so its contrast is the tested value.
   */
  glow: 'radial-gradient(circle at 70% 25%, rgba(216, 242, 60, 0.4) 0%, rgba(216, 242, 60, 0) 55%)',
  text: palette.white,
  textMuted: '#c8ccbd',
  border: '#3b3f35',
  highlight: palette.lime,
  onHighlight: palette.ink,
} as const;

/**
 * Font families, loaded in the root layout. On Android a custom font plus `fontWeight`
 * can silently fall back to the system font, so each weight is its own family and we
 * never set `fontWeight` alongside these.
 */
export const fonts = {
  display: 'Urbanist_700Bold',
  displayBold: 'Urbanist_600SemiBold',
  body: 'Urbanist_500Medium',
  medium: 'Urbanist_600SemiBold',
  bold: 'Urbanist_700Bold',
} as const;

// A 4-point scale: every gap and padding is one of these, which keeps layouts even.
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

// Soft and round throughout: nothing sharp.
export const radius = { sm: 8, md: 14, lg: 20, xl: 28, hero: 32, pill: 999 } as const;

export const type = {
  display: { fontFamily: fonts.display, fontSize: 34, lineHeight: 40, letterSpacing: -0.6 },
  title: { fontFamily: fonts.display, fontSize: 28, lineHeight: 34, letterSpacing: -0.4 },
  heading: { fontFamily: fonts.displayBold, fontSize: 20, lineHeight: 26, letterSpacing: -0.2 },
  body: { fontFamily: fonts.body, fontSize: 16, lineHeight: 23 },
  label: { fontFamily: fonts.bold, fontSize: 15, lineHeight: 20 },
  caption: { fontFamily: fonts.body, fontSize: 13, lineHeight: 18 },
  pill: { fontFamily: fonts.bold, fontSize: 12, lineHeight: 16 },
} as const;

/** CSS-style shadows (supported on iOS, Android and web with the New Architecture). */
export const shadow = {
  card: '0px 4px 14px -8px rgba(0, 0, 0, 0.30)',
  raised: '0px 12px 28px -14px rgba(0, 0, 0, 0.40)',
} as const;

/**
 * Motion. One feel for the whole app: springy, quick, never slow.
 * - pop: ticks and checkboxes overshoot, then settle.
 * - press: buttons shrink slightly while held.
 * - gentle: toasts and sheets slide in.
 * Every animation is switched off when the device's "reduce motion" setting is on.
 */
export const motion = {
  duration: { fast: 150, base: 250, slow: 400 },
  spring: {
    pop: { damping: 9, stiffness: 320, mass: 0.7 },
    press: { damping: 20, stiffness: 400 },
    gentle: { damping: 18, stiffness: 200 },
  },
  pressScale: 0.97,
  staggerMs: 45,
} as const;

/** Height of the bottom tab bar, above the phone's home-bar area. Toasts sit above it. */
export const tabBarHeight = 64;

/** Minimum tappable size (Apple HIG 44pt). Applies to every button and row. */
export const touchTarget = 44;
