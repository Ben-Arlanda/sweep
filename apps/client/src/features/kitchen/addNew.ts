/**
 * The Kitchen's "Add 'kale'" offer (ADR 0012): when search finds nothing called exactly
 * what the Member typed, offer to add it. The server makes it a Household Ingredient,
 * or returns the Ingredient the name already means.
 */

const NAME_MAX = 80; // ingredients.name is VARCHAR(80)

/**
 * Same as the server's `ingredients.normalise`: lower-case, punctuation to spaces,
 * single spaces. `\p{L}\p{N}` (with the `u` flag) matches letters and digits in any
 * language, like Python's `\w`; JavaScript's own `\w` is ASCII only.
 */
export function normalise(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}_\s-]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .join(' ');
}

/** The name to offer adding, or null if search already has it or it isn't usable. */
export function newIngredientName(query: string, resultNames: readonly string[]): string | null {
  const name = normalise(query);
  if (name.length < 2 || name.length > NAME_MAX) return null;
  return resultNames.includes(name) ? null : name;
}
