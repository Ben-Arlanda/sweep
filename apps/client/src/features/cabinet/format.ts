/**
 * How Cabinet amounts read on screen. The API always sends the Ingredient's base unit
 * (g, ml or count); people read "1.5 kg" more easily than "1500 g".
 */
type Status = 'confirmed' | 'estimated' | 'unknown';

export function formatAmount(quantity: string | null, unit: string): string {
  if (quantity === null) return 'Some';
  const n = Number(quantity);
  const trim = (x: number) => String(Number(x.toFixed(2)));
  if (unit === 'g') return n >= 1000 ? `${trim(n / 1000)} kg` : `${trim(n)} g`;
  if (unit === 'ml') return n >= 1000 ? `${trim(n / 1000)} L` : `${trim(n)} ml`;
  return trim(n);
}

export const STATUS_LABEL: Record<Status, string> = {
  confirmed: 'Confirmed',
  estimated: 'Estimated',
  unknown: 'Unknown, please check',
};

/** Unknown amounts are the ones the app (and later the agent) shouldn't rely on. */
export function needsAttention(status: Status): boolean {
  return status === 'unknown';
}
