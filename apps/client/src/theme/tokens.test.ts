import { contrastRatio } from './contrast';
import { initials, tintFor } from './tint';
import {
  colors,
  hero,
  homeColors,
  PAGE_COLORS,
  statusColors,
  stockColors,
  TINT_NAMES,
  tints,
} from './tokens';

const AA = 4.5;
const schemes = ['light', 'dark'] as const;

describe('contrastRatio', () => {
  it('matches known values', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 0);
    expect(contrastRatio('#ffffff', '#ffffff')).toBeCloseTo(1, 5);
  });

  it('catches the trap this palette sets: lime text on white', () => {
    expect(contrastRatio('#d8f23c', '#ffffff')).toBeLessThan(1.5);
  });
});

describe.each(schemes)('%s theme meets WCAG AA for text', (scheme) => {
  const c = colors[scheme];

  it.each([
    ['text on background', c.text, c.background],
    ['text on surface', c.text, c.surface],
    ['muted text on background', c.textMuted, c.background],
    ['muted text on surface', c.textMuted, c.surface],
    ['button text on lime', c.onAction, c.action],
    ['button text on pressed lime', c.onAction, c.actionPressed],
    ['text on soft lime', c.onActionSoft, c.actionSoft],
    ['toast text', c.onInverse, c.inverse],
    ['strong button text', c.onStrong, c.strong],
    ['lavender button text', c.onLavender, c.lavender],
    ['danger on background', c.danger, c.background],
    ['danger on surface', c.danger, c.surface],
    ['danger on soft danger', c.danger, c.dangerSoft],
    ['text on the chef yellow', c.onChef, c.chef],
    ['text on a grey pill (On list)', c.text, c.border],
    ['hero title', c.onHero, c.hero],
    ['hero text', c.onHeroMuted, c.hero],
    ['hero search text', c.onHero, c.heroField],
    ['hero search placeholder', c.onHeroMuted, c.heroField],
    ['lime highlight in the hero', c.onAction, c.action],
  ])('%s', (_, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(AA);
  });

  it.each(TINT_NAMES)('%s tint: card text and quantity pill', (name) => {
    const t = tints[scheme][name];
    expect(contrastRatio(t.text, t.bg)).toBeGreaterThanOrEqual(AA);
    expect(contrastRatio(t.onPill, t.pill)).toBeGreaterThanOrEqual(AA);
  });

  it.each(['confirmed', 'estimated', 'unknown', 'runOut'] as const)('%s status badge', (name) => {
    const s = statusColors[scheme][name];
    // A transparent badge sits on the card surface.
    const bg = s.bg === 'transparent' ? c.surface : s.bg;
    expect(contrastRatio(s.fg, bg)).toBeGreaterThanOrEqual(AA);
  });
});

describe.each(schemes)('%s stock colours (ADR 0024)', (scheme) => {
  const c = colors[scheme];
  it.each(['in_stock', 'low', 'out'] as const)('%s badge, tile text and icon', (name) => {
    const s = stockColors[scheme][name];
    expect(contrastRatio(s.fg, s.bg)).toBeGreaterThanOrEqual(AA);
    expect(contrastRatio(c.text, s.tile)).toBeGreaterThanOrEqual(AA);
    expect(contrastRatio(s.icon, s.tile)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(s.icon, c.surface)).toBeGreaterThanOrEqual(3);
  });
});

describe.each(schemes)('%s controls are visible (3:1, WCAG 1.4.11)', (scheme) => {
  it('the selected Staples / Non-staples tab (text on green)', () => {
    expect(
      contrastRatio(colors[scheme].surface, colors[scheme].tabSelected),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it('a switch that is off', () => {
    expect(contrastRatio(colors[scheme].switchOff, colors[scheme].surface)).toBeGreaterThanOrEqual(
      3,
    );
  });
});

describe('welcome hero meets WCAG AA', () => {
  it.each([
    ['headline', hero.text, hero.background],
    ['body text', hero.textMuted, hero.background],
    ['highlighted words', hero.onHighlight, hero.highlight],
  ])('%s', (_, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(AA);
  });

  it.each(TINT_NAMES)('%s card on the hero keeps its light pastel', (name) => {
    expect(contrastRatio(tints.light[name].text, tints.light[name].bg)).toBeGreaterThanOrEqual(AA);
  });
});

describe('tintFor', () => {
  it('is stable for the same key', () => {
    expect(tintFor('bob')).toBe(tintFor('bob'));
  });

  it('spreads keys across every tint', () => {
    const seen = new Set(Array.from({ length: 50 }, (_, i) => tintFor(`member-${i}`)));
    expect(seen.size).toBe(TINT_NAMES.length);
  });
});

describe('initials', () => {
  it.each([
    ['Alice Smith', 'AS'],
    ['bob', 'B'],
    ['  Mary   Jane Watson ', 'MJ'],
    ['', ''],
  ])('%j → %j', (name, expected) => {
    expect(initials(name)).toBe(expected);
  });
});

describe("Home's blue page (homeColors) meets WCAG AA", () => {
  const c = { ...colors.light, ...homeColors };

  it.each([
    ['page text on the blue', c.onBackground, c.background],
    ['muted page text on the blue', c.onBackgroundMuted, c.background],
    ['hero title on the blue', c.onHero, c.background],
    ['hero subtitle on the blue', c.onHeroMuted, c.background],
    ['card text on warm white', c.text, c.surface],
    ['muted card text on warm white', c.textMuted, c.surface],
    ['field text on warm white', c.text, c.heroField],
  ])('%s', (_name, fg, bg) => {
    expect(contrastRatio(fg as string, bg as string)).toBeGreaterThanOrEqual(AA);
  });

  it('lime words in the Home title read on the blue (AA text)', () => {
    expect(contrastRatio(c.action, c.background)).toBeGreaterThanOrEqual(AA);
  });

  it('lime buttons stand out from the blue (3:1 for controls)', () => {
    expect(contrastRatio(c.action, c.background)).toBeGreaterThanOrEqual(3);
  });

  it('ink text would fail on the blue, which is why onBackground exists', () => {
    expect(contrastRatio(c.text, c.background)).toBeLessThan(AA);
  });
});

describe.each(Object.keys(PAGE_COLORS) as (keyof typeof PAGE_COLORS)[])(
  'the %s page colour meets WCAG AA',
  (page) => {
    const c = { ...colors.light, ...PAGE_COLORS[page] };
    it.each([
      ['page text', c.onBackground, c.background],
      ['muted page text', c.onBackgroundMuted, c.background],
      ['hero title', c.onHero, c.background],
      ['hero subtitle', c.onHeroMuted, c.background],
      ['card text on warm white', c.text, c.surface],
    ])('%s', (_name, fg, bg) => {
      expect(contrastRatio(fg as string, bg as string)).toBeGreaterThanOrEqual(AA);
    });
  },
);

describe('lime words in a large hero title (34pt: AA large text is 3:1)', () => {
  it.each(['home', 'recipes'] as const)('read on the %s page', (page) => {
    const c = { ...colors.light, ...PAGE_COLORS[page] };
    expect(contrastRatio(c.action, c.background)).toBeGreaterThanOrEqual(3);
  });
});
