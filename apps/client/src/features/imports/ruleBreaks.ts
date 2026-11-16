/**
 * Why Sweep won't plan one of "Your recipes". The server sends each reason as
 * "soy sauce (gluten free)" or "satay sauce (couldn't check)": the line, then which
 * Dietary Rule it breaks, or that Sweep can't tell (Rules fail closed).
 */
export function ruleBreakText(breaks: string[]): string | null {
  if (breaks.length === 0) return null;
  const shown = breaks.slice(0, 3).join(', ');
  const more = breaks.length > 3 ? ` and ${breaks.length - 3} more` : '';
  return `Not planned with your Dietary Rules: ${shown}${more}.`;
}

/** Extra help when the only problem is lines Sweep couldn't check: linking fixes those. */
export function ruleBreakHint(breaks: string[]): string | null {
  return breaks.length > 0 && breaks.every((b) => b.endsWith("(couldn't check)"))
    ? 'Edit the recipe and link those lines to an Ingredient Sweep knows.'
    : null;
}
