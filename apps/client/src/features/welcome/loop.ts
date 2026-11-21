/**
 * How visible a piece of an onboarding animation is at point `p` (0 to 1) of its loop:
 * 0 before `start`, fading in to 1, held, then fading out by `end`.
 */
export function shownAt(p: number, start: number, end: number, fade = 0.06): number {
  'worklet';
  if (p <= start || p >= end) return 0;
  return Math.min(1, (p - start) / fade, (end - p) / fade);
}
