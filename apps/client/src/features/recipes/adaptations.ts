/**
 * Recipe Adaptations (ADR 0021): a recipe with some ingredient lines swapped, kept under
 * its parent for the Household. The method isn't rewritten, so the screen shows the
 * Swaps above it ("brown the beef" may still be there in a lentil ragu).
 */

export type Swap = { replaces: string; raw_text: string };

/** Same join the server uses for the saved title (`adaptations.TITLE_JOIN`). */
const TITLE_JOIN = ' · ';

/**
 * A Proposal meal's name. Before approval the server sends the parent's title and the
 * label apart ("with brown lentils"); approving saves them joined, so show them joined.
 */
export function adaptedTitle(meal: {
  title: string;
  adaptation?: { label: string } | null;
}): string {
  return meal.adaptation ? `${meal.title}${TITLE_JOIN}${meal.adaptation.label}` : meal.title;
}

/**
 * "400 g brown lentils instead of 500 g beef mince". Words, not an arrow: a screen reader
 * says "→" as "right arrow", and the new line first is what you'll actually buy.
 */
export function swapLine(swap: Swap): string {
  return `${swap.raw_text} instead of ${swap.replaces}`;
}

/** The swapped lines of an Adaptation (each one knows the parent line it replaced). */
export function swapsOf(lines: { raw_text: string; replaces?: string | null }[]): Swap[] {
  return lines.flatMap((line) =>
    line.replaces ? [{ replaces: line.replaces, raw_text: line.raw_text }] : [],
  );
}
