/**
 * WCAG contrast ratio between two colours (1 = identical, 21 = black on white).
 * AA needs 4.5 for normal text and 3 for large text and icons.
 *
 * Why it's computed, not eyeballed: bright palettes are where contrast quietly fails.
 * Lime looks vivid, but lime text on white is about 1.3:1, which is unreadable.
 */
export function contrastRatio(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

function luminance(hex: string): number {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) throw new Error(`Expected #rrggbb, got ${hex}`);
  const n = parseInt(m[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
