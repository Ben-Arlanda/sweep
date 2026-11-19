import { contrastRatio, mix } from './contrast';
import { initials, tintFor } from './tint';
import {
  colors,
  hero,
  PAGE_COLORS,
  palette,
  statusColors,
  TAB_BAR_FROST,
  TAB_PILL_SHADE,
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
  // A see-through hero shows the page under it.
  const heroBg = c.hero === 'transparent' ? c.background : c.hero;

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
    ['solid danger button text', c.onDanger, c.danger],
    ['danger on background', c.danger, c.background],
    ['danger on surface', c.danger, c.surface],
    ['danger on soft danger', c.danger, c.dangerSoft],
    ['text on the chef yellow', c.onChef, c.chef],
    ['text on a grey pill (On list)', c.text, c.border],
    ['hero title', c.onHero, heroBg],
    ['hero text', c.onHeroMuted, heroBg],
    ['hero search text', c.onHero, c.heroField],
    ['hero search placeholder', c.onHeroMuted, c.heroField],
    ['lime highlight in the hero', c.onAction, c.action],
    ['text on a selected chip', c.onSelected, c.selected],
    ['text on the quiet fill', c.text, c.fill],
    ['muted text on the quiet fill', c.textMuted, c.fill],
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

describe('floating tab bar meets WCAG AA', () => {
  it('labels on the frost, even over black content', () => {
    const worst = mix(palette.paper, palette.ink, TAB_BAR_FROST);
    expect(contrastRatio(palette.ink700, worst)).toBeGreaterThanOrEqual(AA);
  });
  it('a selected chip stands out from the page (3:1, WCAG 1.4.11)', () => {
    expect(contrastRatio(palette.navy, palette.page)).toBeGreaterThanOrEqual(3);
  });
  it('selected label on its navy pill, even over black content', () => {
    const pill = mix(palette.navy, mix(palette.paper, palette.ink, TAB_BAR_FROST), TAB_PILL_SHADE);
    expect(contrastRatio(palette.ink, pill)).toBeGreaterThanOrEqual(AA);
  });
});
