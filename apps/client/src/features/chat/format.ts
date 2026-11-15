import { formatAmount } from '@/features/cabinet/format';

/**
 * "2026-11-16" → "Mon 16 Nov". Built from the parts, because `new Date('2026-11-16')`
 * means midnight UTC, which is the day before for anyone west of Greenwich.
 */
export function formatDay(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  const weekday = date.toLocaleDateString('en-AU', { weekday: 'short' });
  const month = date.toLocaleDateString('en-AU', { month: 'short' });
  return `${weekday} ${date.getDate()} ${month}`;
}

/** "6 eggs", "1.2 kg canned tomatoes", "1 bunch coriander", or just "garlic". */
export function formatAddition(item: {
  name: string;
  quantity: number | null;
  unit: string | null;
}): string {
  if (item.quantity === null) return item.name;
  const unit = item.unit ?? 'count';
  const amount =
    unit === 'g' || unit === 'ml' || unit === 'count'
      ? formatAmount(String(item.quantity), unit) // g → kg, ml → L, count → just the number
      : `${item.quantity} ${unit}`;
  return `${amount} ${item.name}`;
}
