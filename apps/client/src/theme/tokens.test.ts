import { contrastRatio } from './contrast';
import { initials, tintFor } from './tint';
import { colors, hero, statusColors, TINT_NAMES, tints } from './tokens';

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
    ['danger on background', c.danger, c.background],
    ['danger on surface', c.danger, c.surface],
    ['danger on soft danger', c.danger, c.dangerSoft],
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
