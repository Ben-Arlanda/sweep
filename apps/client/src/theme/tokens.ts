/**
 * Design tokens: the app's shared visual decisions, named once and used everywhere.
 *
 * Direction: "Lime & Navy" on the Warm Neutral layout (premium redesign, 2026-11-19): one
 * cool neutral page, white cards with a hairline edge, navy ink, and lime kept for the one
 * main action and Sweep's AI.
 *
 * Components never hard-code a colour or a spacing value. They ask for a *role*
 * ("action", "textMuted", a tint) rather than a raw colour, so each colour has one job:
 * - Lime is for actions only (main buttons, ticks, the AI). Never text on white.
 * - Pastel tints give each list, Member and item its own colour. Quantity pills use a
 *   deeper shade of the same tint ("matched tint").
 * - Kitchen statuses have their own colours so they never get confused with the brand.
 *
 * Contrast for every text/background pair is checked in tokens.test.ts.
 */

export const palette = {
  lime: '#d8f23c',
  limePressed: '#c5de25',
  limeSoft: '#eef8b8',
  chef: '#fcb608', // the chef mascot's golden yellow, sampled from his artwork
  ink: '#121a2e', // navy ink
  ink700: '#2b3550',
  navy: '#1b2a4e', // selection: chips, segmented tabs, step numbers
  page: '#f1f3f7', // the one page colour on every tab
  line: '#dce0e9',
  fill: '#e4e8f0', // photo placeholders and quiet fills
  aiSoft: '#eef6c8',
  paper: '#ffffff',
  white: '#ffffff',
  stone600: '#4f5770',
  stone300: '#dce0e9',
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
  /** Quiet fill: photo placeholders, segmented-control tracks. */
  fill: string;
  /** Lime: main buttons, ticks, the AI. */
  action: string;
  actionPressed: string;
  onAction: string;
  actionSoft: string;
  onActionSoft: string;
  /** Selection (chips, segmented tabs): navy, white text on it. Lime stays for actions. */
  selected: string;
  onSelected: string;
  /** Smaller, quieter text on navy (the weekday over the date). */
  onSelectedMuted: string;
  /** The one strong dark (light in dark mode) surface: toasts and anchor cards. */
  inverse: string;
  onInverse: string;
  danger: string;
  dangerSoft: string;
  /** A switch's track when off: dark enough to see on a card (3:1, like any control). */
  switchOff: string;
  /** The selected Staples / Non-staples tab: deep green, card-coloured text on it. */
  tabSelected: string;
  /**
   * The rounded panel at the top of the main screens. Pale lime on the light theme; on
   * the dark theme a lighter green-grey, so it still stands out from the page.
   */
  hero: string;
  onHero: string;
  onHeroMuted: string;
  /** The search field inside the hero. */
  heroField: string;
  /** The chef mascot's yellow, for anything drawn to match him. Ink text only on it. */
  chef: string;
  onChef: string;
  /** Text straight on the page (not on a card): ink on paper; white on Home's blue. */
  onBackground: string;
  onBackgroundMuted: string;
  /** Bottom sheets and dialogs: their own colour, so a screen's page colour can't reach them. */
  sheet: string;
  /** Near-black for one strong button (View recipe), white text on it. */
  strong: string;
  onStrong: string;
  /** Soft lavender for a gentle button (Home's View recipe), ink text on it. */
  lavender: string;
  onLavender: string;
  /** Text on a solid danger button ("Yes, delete my account"). */
  onDanger: string;
};

export const colors: Record<'light' | 'dark', ColorTokens> = {
  light: {
    background: palette.page,
    surface: palette.white,
    text: palette.ink,
    textMuted: palette.stone600,
    border: palette.line,
    fill: palette.fill,
    action: palette.lime,
    actionPressed: palette.limePressed,
    onAction: palette.ink,
    actionSoft: palette.aiSoft,
    onActionSoft: '#2f3600',
    selected: palette.navy,
    onSelected: palette.white,
    onSelectedMuted: '#d9dccf',
    inverse: palette.ink,
    onInverse: palette.white,
    danger: palette.red600,
    dangerSoft: palette.red100,
    switchOff: '#858ca0',
    tabSelected: palette.navy,
    hero: 'transparent',
    onHero: palette.ink,
    onHeroMuted: palette.stone600,
    heroField: palette.white,
    chef: palette.chef,
    onChef: palette.ink,
    onBackground: palette.ink,
    onBackgroundMuted: palette.stone600,
    sheet: palette.white,
    strong: palette.navy,
    onStrong: palette.white,
    lavender: '#e4e8f0',
    onLavender: palette.ink,
    onDanger: palette.white,
  },
  dark: {
    background: palette.night900,
    fill: palette.night700,
    selected: palette.mist100,
    onSelected: palette.ink,
    onSelectedMuted: palette.ink700,
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
    switchOff: '#6b7262',
    tabSelected: '#bfe8c3',
    hero: '#262b21',
    onHero: palette.mist100,
    onHeroMuted: '#bfc4b3',
    heroField: '#353b2e',
    chef: palette.chef,
    onChef: palette.ink,
    onBackground: palette.mist100,
    onBackgroundMuted: palette.mist400,
    sheet: palette.night900,
    strong: '#171a14',
    onStrong: palette.white,
    lavender: '#e9deff',
    onLavender: palette.ink,
    onDanger: palette.ink,
  },
};

/**
 * Each main screen's page colour. Since the premium redesign (2026-11-19) every tab shares
 * the one neutral page; the map stays so a screen could get its own colour again.
 */
const neutralPage = {
  background: palette.page,
  surface: palette.white,
  hero: 'transparent',
  onHero: palette.ink,
  onHeroMuted: palette.stone600,
  heroField: palette.white,
  onBackground: palette.ink,
  onBackgroundMuted: palette.stone600,
} satisfies Partial<ColorTokens>;

export const PAGE_COLORS = {
  home: neutralPage,
  kitchen: neutralPage,
  list: neutralPage,
  recipes: neutralPage,
  plan: neutralPage,
  household: neutralPage,
};
export type Page = keyof typeof PAGE_COLORS;

/**
 * Each tab's small icon tile (Home's quick tiles, section headers): a pale wash with the
 * icon in a deeper shade of the same colour. Graphics only need 3:1 on their wash.
 */
export const sectionTints = {
  home: { bg: '#e3e8fa', fg: '#2447c6' },
  list: { bg: '#fbe3dc', fg: '#a63d22' },
  kitchen: { bg: '#d6efeb', fg: '#006b61' },
  plan: { bg: '#fcefd2', fg: '#8a5a00' },
  recipes: { bg: '#ebe4fa', fg: '#6343b8' },
} as const;

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

/** Kitchen statuses (ADR 0003), deliberately not lime so they never read as "tap me". */
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
 * Stock the Member sets (ADR 0024): green In stock, amber Running low, red Out. `tile` is
 * the summary tile, `bg`/`fg` the badge, `icon` the symbol (graphics need only 3:1).
 */
export type StockName = 'in_stock' | 'low' | 'out';
export type StockColors = { tile: string; bg: string; fg: string; icon: string };

export const stockColors: Record<'light' | 'dark', Record<StockName, StockColors>> = {
  light: {
    in_stock: { tile: '#e6f5df', bg: '#e1f2d9', fg: '#1d5e27', icon: '#2f8f3c' },
    low: { tile: '#fff3dc', bg: '#ffefd0', fg: '#7f4400', icon: '#c46f00' },
    out: { tile: '#fde4e1', bg: '#fde0dc', fg: palette.red700, icon: '#d6342a' },
  },
  dark: {
    in_stock: { tile: '#1c3020', bg: '#22402a', fg: '#bfe8c3', icon: '#6fd17d' },
    low: { tile: '#38290f', bg: '#4a3510', fg: '#ffd98a', icon: '#f2a93b' },
    out: { tile: '#3e1d19', bg: '#4a1f19', fg: palette.red300, icon: '#ff7a6b' },
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
  display: 'Urbanist_600SemiBold', // screen titles only
  displayBold: 'Inter_600SemiBold',
  body: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  bold: 'Inter_600SemiBold',
} as const;

// A 4-point scale: every gap and padding is one of these, which keeps layouts even.
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

// Buttons and fields 12, cards 16, sheets 24, chips fully round.
export const radius = { sm: 8, md: 12, lg: 16, xl: 24, hero: 24, pill: 999 } as const;

export const type = {
  display: { fontFamily: fonts.display, fontSize: 34, lineHeight: 40, letterSpacing: -0.6 },
  title: { fontFamily: fonts.display, fontSize: 30, lineHeight: 36, letterSpacing: -0.4 },
  heading: { fontFamily: fonts.displayBold, fontSize: 18, lineHeight: 24, letterSpacing: -0.2 },
  body: { fontFamily: fonts.body, fontSize: 15, lineHeight: 22 },
  label: { fontFamily: fonts.bold, fontSize: 15, lineHeight: 20 },
  caption: { fontFamily: fonts.body, fontSize: 13, lineHeight: 18 },
  pill: { fontFamily: fonts.bold, fontSize: 12, lineHeight: 16 },
} as const;

/**
 * CSS-style shadows (iOS, Android and web with the New Architecture). `card` is no shadow
 * at all but a 1px hairline: a spread-only shadow draws the edge without taking up space.
 */
export const shadow = {
  card: `0px 0px 0px 1px ${palette.line}`,
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
export const tabBarHeight = 68;

/**
 * The floating tab bar's frosting: white at this opacity over the blur. High enough that
 * its labels pass AA even over black content (tested in tokens.test.ts).
 */
export const TAB_BAR_FROST = 0.86;
/** The selected tab's pill: navy at this opacity over the frost. */
export const TAB_PILL_SHADE = 0.09;

/** Minimum tappable size (Apple HIG 44pt). Applies to every button and row. */
export const touchTarget = 44;

/**
 * Lucide icon line weights. Thinner than Lucide's default (2) to suit Urbanist; the
 * selected tab uses the heavier one, since Lucide has no filled icons.
 */
export const iconStroke = { regular: 1.5, strong: 2.25 } as const;
