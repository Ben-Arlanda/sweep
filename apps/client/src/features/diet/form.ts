/**
 * Turning what someone typed into values the API accepts, with a message they can act
 * on when it can't. Pure functions, so every odd input is easy to test.
 */

type Parsed<T> = { value: T | null; error: string | null };

export function parseHouseholdSize(text: string): Parsed<number> {
  const trimmed = text.trim();
  if (trimmed === '') return { value: null, error: null }; // optional
  if (/^\d+$/.test(trimmed)) {
    const n = Number(trimmed);
    if (n >= 1 && n <= 20) return { value: n, error: null };
  }
  return { value: null, error: 'Enter a whole number from 1 to 20.' };
}
