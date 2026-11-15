/**
 * Turning what someone typed into values the API accepts, with a message they can act
 * on when it can't. Pure functions, so every odd input is easy to test.
 *
 * Money stays a string ("150.50") all the way to the server. Floats can't hold most
 * cents exactly (0.1 + 0.2 = 0.30000000000000004), and the server stores a Decimal.
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

export function parseBudget(text: string): Parsed<string> {
  const cleaned = text.replace(/[$,\s]/g, '');
  if (cleaned === '') return { value: null, error: null }; // optional
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(cleaned);
  if (match) {
    const dollars = Number(match[1]);
    const cents = (match[2] ?? '').padEnd(2, '0');
    const total = dollars + Number(cents) / 100; // only for the range check
    if (total > 0 && total <= 10_000) return { value: `${dollars}.${cents}`, error: null };
  }
  return { value: null, error: 'Enter an amount up to $10,000, like 150 or 150.50.' };
}

/** How a saved budget appears in the box: "150.00" → "150", "99.50" stays. */
export function budgetText(saved: string | null): string {
  if (saved === null) return '';
  return saved.endsWith('.00') ? saved.slice(0, -3) : saved;
}
